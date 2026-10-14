"""사용자 시나리오 GUI Controller (tkinter).

  python -m user_scenario --gui
  python -m user_scenario.gui

- 시나리오 선택(체크) + 실행 순서 변경(▲/▼)
- 시나리오별 유지 시간, YouTube 영상 수/영상당 재생 시간
- 시나리오 사이 IDLE 시간, 반복 횟수
- 실행/중지, 진행률(현재 단계/전체), 실시간 로그
- TFMonitor 연동: 시작 시 TFMonitor [Start] → FAN0/FAN1 RPM, CPU 온도 로깅 → 종료 후 시나리오별 그래프
- 설정은 ~/.user_scenario_gui.json 에 자동 저장
"""

from __future__ import annotations

import json
import logging
import os
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .config import NAVER_KEYWORDS, QUALITIES, SCENARIOS, YOUTUBE_QUERIES, ScenarioConfig
from .runner import Step, build_plan, planned_total, run_scenario
from .tfmonitor import DEFAULT_TITLE_RE, FIELDS, TFMonitorSettings, default_client_factory, parse_number
from .utils import add_log_handler

SETTINGS_PATH = Path.home() / ".user_scenario_gui.json"
BROWSERS = {"Playwright Chromium": None, "Microsoft Edge": "msedge", "Google Chrome": "chrome"}


def fmt_sec(sec: float | None) -> str:
    if sec is None:
        return "미정"
    sec = int(round(sec))
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


class _QueueLogHandler(logging.Handler):
    """워커 스레드 로그를 GUI 스레드로 전달 (Tk 위젯은 메인 스레드에서만 갱신)."""

    def __init__(self, q: queue.Queue) -> None:
        super().__init__()
        self.q = q

    def emit(self, record: logging.LogRecord) -> None:
        self.q.put(("log", self.format(record), record.levelno))


class ScenarioRow:
    """시나리오 1개 행: [✓] 이름 | 시간 설정 | ▲ ▼"""

    def __init__(self, app: "ControllerApp", parent: ttk.Frame, key: str) -> None:
        self.key = key
        self.enabled = tk.BooleanVar(value=True)
        self.frame = ttk.Frame(parent, padding=(0, 2))
        ttk.Checkbutton(self.frame, text=SCENARIOS[key], variable=self.enabled, width=20).pack(side="left")

        self.vars: dict[str, tk.StringVar] = {}
        if key == "youtube":
            self._spin("video_count", "영상 수", "3", 1, 50, 1, app)
            self._spin("video_seconds", "영상당(s)*", "60", 0, 36000, 10, app)
        else:
            self._spin("seconds", "유지 시간(s)", "60", 1, 36000, 10, app)

        ttk.Button(self.frame, text="▼", width=3, command=lambda: app.move_row(self, +1)).pack(side="right")
        ttk.Button(self.frame, text="▲", width=3, command=lambda: app.move_row(self, -1)).pack(side="right")
        self.enabled.trace_add("write", app.on_change)

    def _spin(self, name: str, label: str, default: str, lo: float, hi: float, inc: float,
              app: "ControllerApp") -> None:
        var = tk.StringVar(value=default)
        var.trace_add("write", app.on_change)
        ttk.Label(self.frame, text=label).pack(side="left", padx=(8, 2))
        ttk.Spinbox(self.frame, from_=lo, to=hi, increment=inc, textvariable=var, width=7).pack(side="left")
        self.vars[name] = var


class ControllerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("User Scenario Controller")
        self.minsize(1100, 700)
        style = ttk.Style(self)
        for theme in ("vista", "clam"):
            if theme in style.theme_names():
                style.theme_use(theme)
                break
        style.configure("Big.TButton", padding=(10, 5))
        style.configure("Status.TLabel", font=("TkDefaultFont", 11, "bold"))

        self.q: queue.Queue = queue.Queue()
        self.log_handler = add_log_handler(_QueueLogHandler(self.q))
        self.worker: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.last_out: Path | None = None
        self._loading = False
        self._run_state: dict = {}
        self.tfmon_client_factory = default_client_factory  # 테스트 시 교체 가능
        self.fan_graph: Path | None = None

        self._build()
        self._load_settings()
        self.on_change()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(100, self._poll)

    # ================================================================== UI
    def _build(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        left = ttk.Frame(root)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right = ttk.Frame(root)
        right.grid(row=0, column=1, sticky="nsew")

        # --- 1. 시나리오 선택 / 순서 / 유지 시간
        sf = ttk.LabelFrame(left, text=" 1. 시나리오 선택 · 순서 · 유지 시간 ", padding=8)
        sf.pack(fill="x")
        self.rows_frame = ttk.Frame(sf)
        self.rows_frame.pack(fill="x")
        self.rows = [ScenarioRow(self, self.rows_frame, key) for key in SCENARIOS]
        self._regrid_rows()
        ttk.Label(sf, text="체크한 시나리오가 위에서부터 순서대로 실행 (▲/▼ 순서 변경) · * 0 = 영상 끝까지",
                  foreground="gray").pack(anchor="w", pady=(4, 0))

        # --- 2. 실행 설정
        rf = ttk.LabelFrame(left, text=" 2. 실행 설정 ", padding=8)
        rf.pack(fill="x", pady=(8, 0))
        self.gap_var = tk.StringVar(value="30")
        self.loops_var = tk.StringVar(value="1")
        self.close_browser_var = tk.BooleanVar(value=True)
        ttk.Label(rf, text="시나리오 사이 IDLE(s)").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(rf, from_=0, to=3600, increment=10, textvariable=self.gap_var, width=7).grid(
            row=0, column=1, sticky="w", padx=4)
        ttk.Label(rf, text="0 = 간격 없음", foreground="gray").grid(row=0, column=2, sticky="w")
        ttk.Label(rf, text="반복 횟수").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Spinbox(rf, from_=1, to=100, increment=1, textvariable=self.loops_var, width=7).grid(
            row=1, column=1, sticky="w", padx=4, pady=(4, 0))
        ttk.Checkbutton(rf, text="IDLE 구간에서는 브라우저 종료 (순수 시스템 idle 측정)",
                        variable=self.close_browser_var).grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))
        for v in (self.gap_var, self.loops_var, self.close_browser_var):
            v.trace_add("write", self.on_change)

        # --- 3. 브라우저 / 측정 옵션
        of = ttk.LabelFrame(left, text=" 3. 브라우저 · 측정 옵션 ", padding=8)
        of.pack(fill="x", pady=(8, 0))
        self.browser_var = tk.StringVar(value="Microsoft Edge" if sys.platform == "win32" else "Playwright Chromium")
        self.browser_path_var = tk.StringVar()
        self.quality_var = tk.StringVar(value="hd1080")
        self.mute_var = tk.BooleanVar(value=False)
        self.headless_var = tk.BooleanVar(value=False)
        self.monitor_var = tk.BooleanVar(value=True)
        self.interval_var = tk.StringVar(value="1.0")
        self.out_var = tk.StringVar(value=str(Path("results").resolve()))

        ttk.Label(of, text="브라우저").grid(row=0, column=0, sticky="w")
        ttk.Combobox(of, textvariable=self.browser_var, values=list(BROWSERS), state="readonly",
                     width=20).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(of, text="실행 파일(선택)").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(of, textvariable=self.browser_path_var, width=26).grid(row=1, column=1, sticky="we", padx=4, pady=(4, 0))
        ttk.Button(of, text="...", width=3, command=self._pick_browser).grid(row=1, column=2, pady=(4, 0))
        ttk.Label(of, text="YouTube 화질").grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Combobox(of, textvariable=self.quality_var, values=QUALITIES, state="readonly",
                     width=10).grid(row=2, column=1, sticky="w", padx=4, pady=(4, 0))
        cb = ttk.Frame(of)
        cb.grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 0))
        ttk.Checkbutton(cb, text="음소거", variable=self.mute_var).pack(side="left")
        ttk.Checkbutton(cb, text="Headless(측정 비권장)", variable=self.headless_var).pack(side="left", padx=8)
        ttk.Checkbutton(cb, text="리소스 모니터링", variable=self.monitor_var).pack(side="left")
        ttk.Label(of, text="샘플링 주기(s)").grid(row=4, column=0, sticky="w", pady=(4, 0))
        ttk.Spinbox(of, from_=0.1, to=60, increment=0.5, textvariable=self.interval_var, width=7).grid(
            row=4, column=1, sticky="w", padx=4, pady=(4, 0))
        ttk.Label(of, text="결과 폴더").grid(row=5, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(of, textvariable=self.out_var, width=26).grid(row=5, column=1, sticky="we", padx=4, pady=(4, 0))
        ttk.Button(of, text="...", width=3, command=self._pick_out).grid(row=5, column=2, pady=(4, 0))

        # --- 4. 키워드 / 영상 목록
        kf = ttk.LabelFrame(left, text=" 4. 네이버 키워드 · YouTube 영상 (한 줄에 하나) ", padding=8)
        kf.pack(fill="both", expand=True, pady=(8, 0))
        kf.columnconfigure((0, 1), weight=1)
        kf.rowconfigure(1, weight=1)
        ttk.Label(kf, text="네이버 검색 키워드 (랜덤 선택)").grid(row=0, column=0, sticky="w")
        ttk.Label(kf, text="YouTube URL 또는 검색어 (순서대로)").grid(row=0, column=1, sticky="w", padx=(6, 0))
        self.keywords_txt = scrolledtext.ScrolledText(kf, width=16, height=5, undo=True)
        self.keywords_txt.grid(row=1, column=0, sticky="nsew")
        self.videos_txt = scrolledtext.ScrolledText(kf, width=22, height=5, undo=True)
        self.videos_txt.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        self.keywords_txt.insert("1.0", "\n".join(NAVER_KEYWORDS))
        self.videos_txt.insert("1.0", "\n".join(YOUTUBE_QUERIES))

        # --- 우측: 실행 계획 / 컨트롤 / 상태 / 로그
        pf = ttk.LabelFrame(right, text=" 실행 계획 ", padding=8)
        pf.pack(fill="x")
        self.plan_lbl = ttk.Label(pf, text="", wraplength=440, justify="left")
        self.plan_lbl.pack(anchor="w")
        self.total_lbl = ttk.Label(pf, text="", style="Status.TLabel")
        self.total_lbl.pack(anchor="w", pady=(4, 0))

        # --- 5. TFMonitor 연동
        tf = ttk.LabelFrame(right, text=" 5. TFMonitor 연동 (FAN RPM · CPU 온도 로깅) ", padding=8)
        tf.pack(fill="x", pady=(8, 0))
        tf.columnconfigure(1, weight=1)
        self.tf_enabled_var = tk.BooleanVar(value=False)
        self.tf_exe_var = tk.StringVar()
        self.tf_title_var = tk.StringVar(value=DEFAULT_TITLE_RE)
        self.tf_interval_var = tk.StringVar(value="1.0")
        self.tf_stop_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tf, text="사용 (Start 클릭 → 종료까지 로깅 → 그래프 생성)",
                        variable=self.tf_enabled_var).grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(tf, text="TFMonitor.exe").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(tf, textvariable=self.tf_exe_var, width=30).grid(row=1, column=1, columnspan=2, sticky="we",
                                                          padx=4, pady=(4, 0))
        ttk.Button(tf, text="...", width=3, command=self._pick_tfmon).grid(row=1, column=3, pady=(4, 0))
        ttk.Label(tf, text="창 제목(정규식)").grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(tf, textvariable=self.tf_title_var, width=16).grid(row=2, column=1, sticky="w", padx=4, pady=(4, 0))
        ttk.Label(tf, text="샘플링(s)").grid(row=2, column=2, sticky="e", pady=(4, 0))
        ttk.Spinbox(tf, from_=0.2, to=60, increment=0.5, textvariable=self.tf_interval_var, width=5).grid(
            row=2, column=3, sticky="w", pady=(4, 0))
        ttk.Checkbutton(tf, text="종료 시 Stop 클릭", variable=self.tf_stop_var).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.tf_test_btn = ttk.Button(tf, text="연결 테스트", command=self.test_tfmonitor)
        self.tf_test_btn.grid(row=3, column=2, columnspan=2, sticky="e", pady=(4, 0))
        for v in (self.tf_enabled_var, self.tf_title_var, self.tf_interval_var):
            v.trace_add("write", self.on_change)

        bf = ttk.Frame(right)
        bf.pack(fill="x", pady=8)
        self.start_btn = ttk.Button(bf, text="▶ 시작", style="Big.TButton", command=self.start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(bf, text="■ 중지", style="Big.TButton", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        ttk.Button(bf, text="저장", width=5, command=lambda: self._save_settings(notify=True)).pack(side="right")
        self.graph_btn = ttk.Button(bf, text="FAN 그래프", command=self.open_fan_graph, state="disabled")
        self.graph_btn.pack(side="right", padx=4)
        ttk.Button(bf, text="결과 폴더", command=self.open_results).pack(side="right")

        stf = ttk.LabelFrame(right, text=" 진행 상태 ", padding=8)
        stf.pack(fill="x")
        stf.columnconfigure(1, weight=1)
        self.status_lbl = ttk.Label(stf, text="대기 중", style="Status.TLabel", wraplength=440)
        self.status_lbl.grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(stf, text="현재 단계").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.step_pb = ttk.Progressbar(stf, maximum=1000)
        self.step_pb.grid(row=1, column=1, sticky="we", padx=6, pady=(6, 0))
        self.step_time_lbl = ttk.Label(stf, text="--:--:-- / --:--:--", width=18)
        self.step_time_lbl.grid(row=1, column=2, sticky="e", pady=(6, 0))
        ttk.Label(stf, text="전체").grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.total_pb = ttk.Progressbar(stf, maximum=1000)
        self.total_pb.grid(row=2, column=1, sticky="we", padx=6, pady=(4, 0))
        self.total_time_lbl = ttk.Label(stf, text="--:--:-- / --:--:--", width=18)
        self.total_time_lbl.grid(row=2, column=2, sticky="e", pady=(4, 0))
        ttk.Label(stf, text="FAN / 온도").grid(row=3, column=0, sticky="w", pady=(4, 0))
        self.fan_lbl = ttk.Label(stf, text="-")
        self.fan_lbl.grid(row=3, column=1, columnspan=2, sticky="w", padx=6, pady=(4, 0))

        lf = ttk.LabelFrame(right, text=" 로그 ", padding=4)
        lf.pack(fill="both", expand=True, pady=(8, 0))
        self.log_txt = scrolledtext.ScrolledText(lf, width=48, height=8, state="disabled", wrap="none",
                                                 font=("Consolas", 9) if sys.platform == "win32" else ("Monospace", 9))
        self.log_txt.pack(fill="both", expand=True)
        self.log_txt.tag_configure("warn", foreground="#b36b00")
        self.log_txt.tag_configure("error", foreground="#c62828")
        self.log_txt.tag_configure("phase", foreground="#1565c0")

        # 설정 입력 위젯 (실행 중 비활성화 대상)
        self._inputs = [w for frame in (sf, rf, of, kf, tf) for w in self._descendants(frame)
                        if isinstance(w, (ttk.Entry, ttk.Spinbox, ttk.Checkbutton, ttk.Combobox,
                                          ttk.Button, scrolledtext.ScrolledText))]

    @staticmethod
    def _descendants(w: tk.Misc) -> list[tk.Misc]:
        out = []
        for c in w.winfo_children():
            out.append(c)
            out += ControllerApp._descendants(c)
        return out

    def _regrid_rows(self) -> None:
        for r in self.rows:
            r.frame.pack_forget()
        for r in self.rows:
            r.frame.pack(fill="x")

    def move_row(self, row: ScenarioRow, delta: int) -> None:
        i = self.rows.index(row)
        j = i + delta
        if 0 <= j < len(self.rows):
            self.rows[i], self.rows[j] = self.rows[j], self.rows[i]
            self._regrid_rows()
            self.on_change()

    def _pick_browser(self) -> None:
        path = filedialog.askopenfilename(title="브라우저 실행 파일 선택")
        if path:
            self.browser_path_var.set(path)

    def _pick_tfmon(self) -> None:
        path = filedialog.askopenfilename(title="TFMonitor 실행 파일 선택",
                                          filetypes=[("실행 파일", "*.exe"), ("모든 파일", "*.*")])
        if path:
            self.tf_exe_var.set(path)

    def _pick_out(self) -> None:
        path = filedialog.askdirectory(title="결과 폴더 선택", initialdir=self.out_var.get())
        if path:
            self.out_var.set(path)

    # ============================================================ config
    def build_config(self) -> ScenarioConfig:
        """UI 값 → ScenarioConfig. 잘못된 값이면 ValueError."""
        def num(var: tk.StringVar, name: str, lo: float, integer: bool = False) -> float:
            try:
                v = int(var.get()) if integer else float(var.get())
            except ValueError:
                raise ValueError(f"'{name}' 값이 숫자가 아닙니다: {var.get()!r}") from None
            if v < lo:
                raise ValueError(f"'{name}' 값은 {lo} 이상이어야 합니다")
            return v

        rows = {r.key: r for r in self.rows}
        scenarios = [r.key for r in self.rows if r.enabled.get()]
        keywords = [l.strip() for l in self.keywords_txt.get("1.0", "end").splitlines() if l.strip()]
        videos = [l.strip() for l in self.videos_txt.get("1.0", "end").splitlines() if l.strip()]
        if "web_surfing" in scenarios and not keywords:
            raise ValueError("네이버 검색 키워드를 1개 이상 입력하세요")
        if "youtube" in scenarios and not videos:
            raise ValueError("YouTube URL 또는 검색어를 1개 이상 입력하세요")
        tf_title = self.tf_title_var.get().strip() or DEFAULT_TITLE_RE
        try:
            re.compile(tf_title)
        except re.error as e:
            raise ValueError(f"TFMonitor 창 제목 정규식 오류: {e}") from None

        return ScenarioConfig(
            scenarios=scenarios,
            gap_idle_seconds=num(self.gap_var, "시나리오 사이 IDLE", 0),
            loops=int(num(self.loops_var, "반복 횟수", 1, integer=True)),
            close_browser_on_idle=self.close_browser_var.get(),
            idle_seconds=num(rows["idle"].vars["seconds"], "IDLE 유지 시간", 1),
            surfing_seconds=num(rows["web_surfing"].vars["seconds"], "웹서핑 유지 시간", 5),
            naver_keywords=keywords or list(NAVER_KEYWORDS),
            youtube_targets=videos or list(YOUTUBE_QUERIES),
            video_count=int(num(rows["youtube"].vars["video_count"], "영상 수", 1, integer=True)),
            video_seconds=num(rows["youtube"].vars["video_seconds"], "영상당 재생 시간", 0),
            video_quality=self.quality_var.get(),
            mute=self.mute_var.get(),
            browser_channel=BROWSERS.get(self.browser_var.get()),
            browser_path=self.browser_path_var.get().strip() or None,
            headless=self.headless_var.get(),
            output_dir=Path(self.out_var.get().strip() or "results"),
            sample_interval=num(self.interval_var, "샘플링 주기", 0.1),
            enable_monitor=self.monitor_var.get(),
            tfmon_enabled=self.tf_enabled_var.get(),
            tfmon_exe=self.tf_exe_var.get().strip() or None,
            tfmon_title_re=tf_title,
            tfmon_interval=num(self.tf_interval_var, "TFMonitor 샘플링 주기", 0.2),
            tfmon_click_stop=self.tf_stop_var.get(),
        )

    def on_change(self, *_) -> None:
        """설정 변경 시 실행 계획 미리보기 갱신."""
        if self._loading or self._run_state:
            return
        try:
            cfg = self.build_config()
            steps = build_plan(cfg)
        except ValueError as e:
            self.plan_lbl.configure(text=f"⚠ {e}", foreground="#c62828")
            self.total_lbl.configure(text="")
            return
        if not steps:
            self.plan_lbl.configure(text="⚠ 실행할 시나리오를 1개 이상 선택하세요", foreground="#c62828")
            self.total_lbl.configure(text="")
            return
        one_loop = [s for s in steps if s.loop == 1]
        seq = " → ".join(f"{self._short(s)}({fmt_sec(s.planned_s)[3:] if s.planned_s else '끝까지'})"
                         for s in one_loop)
        loops = f"  × {cfg.loops}회 반복" if cfg.loops > 1 else ""
        self.plan_lbl.configure(text=f"{seq}{loops}", foreground="")
        tf = " · TFMonitor 로깅 ON" if cfg.tfmon_enabled else ""
        self.total_lbl.configure(text=f"총 {len(steps)} 단계 · 예상 소요 {fmt_sec(planned_total(steps))}{tf}")

    @staticmethod
    def _short(step: Step) -> str:
        return {"idle": "IDLE", "gap_idle": "간격IDLE", "web_surfing": "웹서핑", "youtube": "YouTube"}[step.kind]

    # ============================================================ run
    def start(self) -> None:
        try:
            cfg = self.build_config()
        except ValueError as e:
            messagebox.showerror("설정 오류", str(e))
            return
        if not cfg.scenarios:
            messagebox.showerror("설정 오류", "실행할 시나리오를 1개 이상 선택하세요")
            return
        self._save_settings()
        self.stop_event.clear()
        self._set_running(True)
        self._clear_log()
        self.worker = threading.Thread(target=self._work, args=(cfg,), daemon=True, name="ScenarioWorker")
        self.worker.start()

    def _work(self, cfg: ScenarioConfig) -> None:
        try:
            run_scenario(cfg, self.stop_event, on_event=lambda e: self.q.put(("event", e)),
                         tfmon_client_factory=self.tfmon_client_factory)
        except Exception as e:
            logging.getLogger("scenario").exception("시나리오 실행 오류")
            self.q.put(("fatal", repr(e)))
        finally:
            self.q.put(("finished", None))

    def stop(self) -> None:
        if self.worker and self.worker.is_alive():
            self.stop_event.set()
            self.stop_btn.configure(state="disabled")
            self.status_lbl.configure(text="중지 요청됨 · 진행 중인 브라우저 동작 종료 대기...")

    def _set_running(self, running: bool) -> None:
        for w in self._inputs:
            try:
                w.configure(state="disabled" if running else
                            ("readonly" if isinstance(w, ttk.Combobox) else "normal"))
            except tk.TclError:
                pass
        self.start_btn.configure(state="disabled" if running else "normal")
        self.stop_btn.configure(state="normal" if running else "disabled")
        if running:
            self._run_state = {"t0": time.monotonic()}
            self.status_lbl.configure(text="시작 중...")
            self.fan_lbl.configure(text="연결 중..." if self.tf_enabled_var.get() else "- (TFMonitor 연동 꺼짐)")
            self.fan_graph = None
            self.graph_btn.configure(state="disabled")
        else:
            self._run_state = {}
            self.on_change()

    # ============================================================ queue polling
    def _poll(self) -> None:
        try:
            while True:
                kind, payload, *rest = self.q.get_nowait()
                if kind == "log":
                    self._append_log(payload, rest[0])
                elif kind == "event":
                    self._on_event(payload)
                elif kind == "fatal":
                    messagebox.showerror("실행 오류", payload)
                elif kind == "tftest":
                    self.tf_test_btn.configure(state="normal")
                    (messagebox.showinfo if payload else messagebox.showerror)("TFMonitor 연결 테스트", rest[0])
                elif kind == "finished":
                    self._set_running(False)
        except queue.Empty:
            pass
        self._tick()
        self.after(200, self._poll)

    def _on_event(self, e: dict) -> None:
        st = self._run_state
        if e["event"] == "start":
            st.update(steps=e["steps"], total=e["planned_total"], done_planned=0.0, index=-1)
            self.last_out = Path(e["out"])
            self.total_pb.configure(mode="determinate" if e["planned_total"] else "indeterminate")
            if not e["planned_total"]:
                self.total_pb.start(50)
        elif e["event"] == "step":
            if st.get("index", -1) >= 0:
                st["done_planned"] += st["steps"][st["index"]].planned_s or 0.0
            st.update(index=e["index"], step_t0=time.monotonic())
            step: Step = e["step"]
            self.status_lbl.configure(text=f"[{e['index'] + 1}/{len(st['steps'])}] {step.label}")
            self.step_pb.stop()
            self.step_pb.configure(mode="determinate" if step.planned_s else "indeterminate", value=0)
            if not step.planned_s:
                self.step_pb.start(50)
        elif e["event"] == "fan":
            def f(k, unit, fmt="{:.0f}"):
                return "-" if e.get(k) is None else fmt.format(e[k]) + unit
            self.fan_lbl.configure(text=f"FAN0 {f('fan0_rpm', ' rpm')}  ·  FAN1 {f('fan1_rpm', ' rpm')}  ·  "
                                        f"CPU {f('cpu_temp_c', ' °C', '{:g}')}")
        elif e["event"] == "analysis":
            graphs = [p for p in e["paths"] if p.name == "fan_timeline.png"]
            self.fan_graph = graphs[0] if graphs else None
            self.graph_btn.configure(state="normal" if self.fan_graph else "disabled")
        elif e["event"] == "done":
            self.step_pb.stop()
            self.total_pb.stop()
            self.step_pb.configure(mode="determinate", value=0)
            self.total_pb.configure(mode="determinate", value=0 if e["stopped"] or e["error"] else 1000)
            if e["error"]:
                msg = f"오류로 종료: {e['error']}"
            elif e["stopped"]:
                msg = "사용자 요청으로 중지됨"
            else:
                msg = "완료"
            self.status_lbl.configure(text=f"{msg} · 결과 폴더: {Path(e['out']).name}")

    def _tick(self) -> None:
        st = self._run_state
        if not st or "step_t0" not in st:
            return
        now = time.monotonic()
        step: Step = st["steps"][st["index"]]
        el = now - st["step_t0"]
        self.step_time_lbl.configure(text=f"{fmt_sec(el)} / {fmt_sec(step.planned_s)}")
        if step.planned_s:
            self.step_pb.configure(value=min(1000, 1000 * el / step.planned_s))
        total_el = now - st["t0"]
        self.total_time_lbl.configure(text=f"{fmt_sec(total_el)} / {fmt_sec(st['total'])}")
        if st["total"]:
            done = st["done_planned"] + min(el, step.planned_s or el)
            self.total_pb.configure(value=min(1000, 1000 * done / st["total"]))

    def _append_log(self, msg: str, level: int) -> None:
        tag = "error" if level >= logging.ERROR else "warn" if level >= logging.WARNING else (
            "phase" if "PHASE" in msg else "")
        self.log_txt.configure(state="normal")
        self.log_txt.insert("end", msg + "\n", tag)
        if int(self.log_txt.index("end-1c").split(".")[0]) > 5000:  # 로그 버퍼 상한
            self.log_txt.delete("1.0", "1000.0")
        self.log_txt.see("end")
        self.log_txt.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_txt.configure(state="normal")
        self.log_txt.delete("1.0", "end")
        self.log_txt.configure(state="disabled")

    def test_tfmonitor(self) -> None:
        """TFMonitor 창 연결 → 값 칸 매핑 → 현재 값 1회 읽기 (Start 클릭은 하지 않음)."""
        try:
            cfg = self.build_config()
        except ValueError as e:
            messagebox.showerror("설정 오류", str(e))
            return
        settings = TFMonitorSettings(exe_path=cfg.tfmon_exe, title_re=cfg.tfmon_title_re, backend=cfg.tfmon_backend)
        self.tf_test_btn.configure(state="disabled")

        def work() -> None:
            try:
                from .tfmonitor import _com_init
                _com_init()
                client = self.tfmon_client_factory(settings)
                client.connect(launch=bool(settings.exe_path))
                raw = client.read_raw()
                lines = [f"{FIELDS[k].group} / {FIELDS[k].label}:  {v!r}  →  {parse_number(v)}" for k, v in raw.items()]
                self.q.put(("tftest", True, "연결 성공. 값 칸 매핑 결과:\n\n" + "\n".join(lines)
                            + "\n\n(Start 전에는 값이 비어 있을 수 있습니다)"))
            except Exception as e:
                self.q.put(("tftest", False, f"{e}"))

        threading.Thread(target=work, daemon=True, name="TFMonitorTest").start()

    def open_fan_graph(self) -> None:
        if self.fan_graph and self.fan_graph.exists():
            self._open_path(self.fan_graph)

    def open_results(self) -> None:
        path = self.last_out if self.last_out and self.last_out.exists() else Path(self.out_var.get())
        path.mkdir(parents=True, exist_ok=True)
        self._open_path(path)

    @staticmethod
    def _open_path(path: Path) -> None:
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    # ============================================================ settings
    def _collect_settings(self) -> dict:
        return {
            "order": [r.key for r in self.rows],
            "enabled": {r.key: r.enabled.get() for r in self.rows},
            "values": {r.key: {k: v.get() for k, v in r.vars.items()} for r in self.rows},
            "gap": self.gap_var.get(), "loops": self.loops_var.get(),
            "close_browser": self.close_browser_var.get(),
            "browser": self.browser_var.get(), "browser_path": self.browser_path_var.get(),
            "quality": self.quality_var.get(), "mute": self.mute_var.get(),
            "headless": self.headless_var.get(), "monitor": self.monitor_var.get(),
            "interval": self.interval_var.get(), "out": self.out_var.get(),
            "keywords": self.keywords_txt.get("1.0", "end").strip(),
            "videos": self.videos_txt.get("1.0", "end").strip(),
            "tf_enabled": self.tf_enabled_var.get(), "tf_exe": self.tf_exe_var.get(),
            "tf_title": self.tf_title_var.get(), "tf_interval": self.tf_interval_var.get(),
            "tf_stop": self.tf_stop_var.get(),
        }

    def _save_settings(self, notify: bool = False) -> None:
        try:
            SETTINGS_PATH.write_text(json.dumps(self._collect_settings(), ensure_ascii=False, indent=2),
                                     encoding="utf-8")
            if notify:
                messagebox.showinfo("설정 저장", f"저장됨: {SETTINGS_PATH}")
        except OSError as e:
            if notify:
                messagebox.showerror("설정 저장 실패", str(e))

    def _load_settings(self) -> None:
        try:
            s = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        self._loading = True
        try:
            by_key = {r.key: r for r in self.rows}
            order = [k for k in s.get("order", []) if k in by_key]
            self.rows = [by_key[k] for k in order] + [r for r in self.rows if r.key not in order]
            self._regrid_rows()
            for key, row in by_key.items():
                row.enabled.set(s.get("enabled", {}).get(key, True))
                for name, val in s.get("values", {}).get(key, {}).items():
                    if name in row.vars:
                        row.vars[name].set(val)
            pairs = [(self.gap_var, "gap"), (self.loops_var, "loops"), (self.close_browser_var, "close_browser"),
                     (self.browser_var, "browser"), (self.browser_path_var, "browser_path"),
                     (self.quality_var, "quality"), (self.mute_var, "mute"), (self.headless_var, "headless"),
                     (self.monitor_var, "monitor"), (self.interval_var, "interval"), (self.out_var, "out"),
                     (self.tf_enabled_var, "tf_enabled"), (self.tf_exe_var, "tf_exe"),
                     (self.tf_title_var, "tf_title"), (self.tf_interval_var, "tf_interval"),
                     (self.tf_stop_var, "tf_stop")]
            for var, key in pairs:
                if key in s:
                    var.set(s[key])
            for txt, key in ((self.keywords_txt, "keywords"), (self.videos_txt, "videos")):
                if s.get(key):
                    txt.delete("1.0", "end")
                    txt.insert("1.0", s[key])
        finally:
            self._loading = False

    def on_close(self) -> None:
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno("종료", "시나리오가 실행 중입니다. 중지하고 종료할까요?"):
                return
            self.stop()
            self._wait_and_close()
            return
        self._save_settings()
        self.destroy()

    def _wait_and_close(self) -> None:
        # 워커가 브라우저/결과 파일을 정리할 때까지 대기 후 종료
        if self.worker and self.worker.is_alive():
            self.after(300, self._wait_and_close)
            return
        self._save_settings()
        self.destroy()


def _enable_dpi_awareness() -> None:
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # 고해상도 노트북 화면에서 흐림 방지
        except (AttributeError, OSError):
            pass


def main() -> int:
    _enable_dpi_awareness()
    app = ControllerApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
