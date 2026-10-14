"""TFMonitor(Windows GUI 툴) 연동 - FAN RPM / CPU 온도 로깅.

동작
  1. TFMonitor 창이 떠 있으면 attach, 없으면 exe 실행 후 attach
  2. [Start] 버튼 클릭
  3. 라벨 텍스트 + 화면 좌표로 값 텍스트박스를 찾음
       - FAN Status 그룹: "FAN 0 RPM" / "FAN 1 RPM" 행의 첫 번째 칸 (RPM, 그 오른쪽은 HEX)
       - Micom Data 그룹: "C0 (CPU)" 행의 두 번째 칸 (Hex, [Dec], Max, Avg)
  4. 주기적으로 값을 읽어 CSV 기록 (시나리오 페이즈 태깅)
  5. 시나리오 종료 시 [Stop] 클릭

텍스트박스에 이름(AutomationId)이 없는 WinForms/MFC 앱도 동작하도록
"같은 행(세로 중심 일치) + 라벨 오른쪽 + x 정렬 순서"로 칸을 식별한다.

진단:
  python -m user_scenario.tfmonitor --dump     # 창의 모든 컨트롤(텍스트/클래스/좌표) 출력
  python -m user_scenario.tfmonitor --read     # 값 1회 읽기 (매핑 확인용)
"""

from __future__ import annotations

import csv
import logging
import os
import re
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("scenario.tfmonitor")

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
# "TFMonitor v1.21.0.0" - 같은 이름의 탐색기 폴더 창 등에 잘못 붙지 않도록 버전 표기까지 매칭
DEFAULT_TITLE_RE = r"^TFMonitor v\d"


class TFMonitorError(RuntimeError):
    pass


@dataclass(frozen=True)
class FieldSpec:
    label: str   # 행 라벨 텍스트 (완전 일치, 대소문자/공백 무시)
    group: str   # 소속 그룹박스 제목 (못 찾으면 창 전체에서 검색)
    column: int  # 라벨 오른쪽 텍스트박스 중 몇 번째 칸인지 (0부터)


# 로깅 대상 필드 (CSV 컬럼명 → 위치 정의)
FIELDS: dict[str, FieldSpec] = {
    "fan0_rpm": FieldSpec("FAN 0 RPM", "FAN Status", 0),
    "fan1_rpm": FieldSpec("FAN 1 RPM", "FAN Status", 0),
    "cpu_temp_c": FieldSpec("C0 (CPU)", "Micom Data", 1),
}


def _norm(s: str) -> str:
    return " ".join(s.split()).casefold()


def parse_number(text: str) -> float | None:
    m = _NUM_RE.search(text or "")
    return float(m.group()) if m else None


# --------------------------------------------------------------------------- controls
@dataclass
class _Ctrl:
    """백엔드(win32/uia)와 무관한 컨트롤 스냅샷."""
    wrapper: Any
    text: str
    kind: str  # edit | button | other
    left: int
    top: int
    right: int
    bottom: int

    @property
    def cy(self) -> float:
        return (self.top + self.bottom) / 2

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def inside(self, o: "_Ctrl") -> bool:
        return o.left <= self.left and self.right <= o.right and o.top <= self.top and self.bottom <= o.bottom


def _kind(w: Any) -> str:
    ct = getattr(w.element_info, "control_type", None)  # uia 백엔드
    if ct:
        return {"Edit": "edit", "Button": "button"}.get(ct, "other")
    cls = (w.class_name() or "").upper()  # win32 백엔드 (WindowsForms10.EDIT.app..., Edit, Button)
    fc = w.friendly_class_name()
    if fc == "Edit" or ".EDIT." in cls or cls == "EDIT":
        return "edit"
    if fc == "Button":
        return "button"
    return "other"


def find_row_edits(ctrls: list[_Ctrl], spec: FieldSpec) -> _Ctrl:
    """spec 에 해당하는 텍스트박스를 좌표 기반으로 찾는다."""
    groups = [c for c in ctrls if _norm(c.text) == _norm(spec.group) and c.kind != "edit"
              and c.height > 40]
    scope = [c for c in ctrls if c.inside(groups[0])] if groups else ctrls
    labels = [c for c in scope if c.kind != "edit" and _norm(c.text) == _norm(spec.label)]
    if not labels:
        raise TFMonitorError(f"라벨 '{spec.label}' 을(를) '{spec.group}' 영역에서 찾지 못함")
    label = labels[0]
    row = [c for c in scope if c.kind == "edit" and c.left >= label.left + 5
           and abs(c.cy - label.cy) <= max(label.height, c.height) * 0.75]
    row.sort(key=lambda c: c.left)
    if len(row) <= spec.column:
        raise TFMonitorError(
            f"'{spec.label}' 행에서 {spec.column + 1}번째 값 칸을 찾지 못함 (찾은 칸 {len(row)}개)")
    return row[spec.column]


class TFMonitorClient:
    def __init__(self, exe_path: str | None = None, title_re: str = DEFAULT_TITLE_RE,
                 backend: str = "win32", timeout: float = 30.0) -> None:
        if sys.platform != "win32":
            raise TFMonitorError("TFMonitor 연동은 Windows 에서만 지원됩니다")
        import importlib.util
        if importlib.util.find_spec("pywinauto") is None:
            raise TFMonitorError("pywinauto 미설치: pip install pywinauto")
        self.exe_path = exe_path
        self.title_re = title_re
        self.backend = backend
        self.timeout = timeout
        self.app = None
        self.win = None
        self.launched = False
        self.edits: dict[str, Any] = {}

    # ---------------------------------------------------------------- connect
    def connect(self, launch: bool = True) -> None:
        from pywinauto import Application
        from pywinauto.findwindows import ElementNotFoundError

        try:
            self.app = Application(backend=self.backend).connect(title_re=self.title_re, found_index=0, timeout=1)
            log.info("실행 중인 TFMonitor 에 연결")
        except ElementNotFoundError:
            if not (launch and self.exe_path):
                raise TFMonitorError(
                    f"TFMonitor 창(title~'{self.title_re}')을 찾지 못함 - 먼저 실행하거나 exe 경로를 지정하세요"
                ) from None
            self._launch()
            self.app = Application(backend=self.backend).connect(title_re=self.title_re, found_index=0,
                                                                 timeout=self.timeout)
            self.launched = True
        spec = self.app.window(title_re=self.title_re, found_index=0)
        spec.wait("visible", timeout=self.timeout)
        self.win = spec.wrapper_object()
        log.info("TFMonitor 창: '%s'", self.win.window_text())

    def _launch(self) -> None:
        path = Path(self.exe_path)
        if not path.is_file():
            raise TFMonitorError(f"TFMonitor 실행 파일이 없음: {path}")
        log.info("TFMonitor 실행: %s", path)
        import subprocess
        try:
            # 설정/드라이버 파일을 상대 경로로 읽는 툴이 많으므로 작업 폴더를 exe 위치로 지정
            subprocess.Popen([str(path)], cwd=str(path.parent))
        except OSError as e:
            if getattr(e, "winerror", None) == 740:  # ERROR_ELEVATION_REQUIRED
                log.warning("TFMonitor 가 관리자 권한을 요구 → UAC 승인 후 실행 "
                            "(값 읽기/버튼 클릭을 위해 이 프로그램도 관리자 권한으로 실행 권장)")
                os.startfile(str(path))  # noqa: S606 - ShellExecute 로 UAC 프롬프트
            else:
                raise

    def snapshot(self) -> list[_Ctrl]:
        out = []
        for w in self.win.descendants():
            try:
                if not w.is_visible():
                    continue
                r = w.rectangle()
                out.append(_Ctrl(w, w.window_text() or "", _kind(w), r.left, r.top, r.right, r.bottom))
            except Exception:
                continue
        return out

    # ---------------------------------------------------------------- actions
    def press(self, caption: str) -> None:
        btns = [c for c in self.snapshot() if c.kind == "button" and _norm(c.text) == _norm(caption)]
        if not btns:
            raise TFMonitorError(f"'{caption}' 버튼을 찾지 못함")
        w = btns[0].wrapper
        # win32: BM_CLICK 메시지 → 포커스/마우스 이동 없이 클릭 (브라우저 포커스 유지)
        if hasattr(w, "invoke") and self.backend == "uia":
            w.invoke()
        else:
            w.click()
        log.info("TFMonitor [%s] 클릭", caption)

    def resolve(self) -> dict[str, Any]:
        ctrls = self.snapshot()
        self.edits = {name: find_row_edits(ctrls, spec).wrapper for name, spec in FIELDS.items()}
        return self.edits

    def read_raw(self) -> dict[str, str]:
        if not self.edits:
            self.resolve()
        out = {}
        for name, w in self.edits.items():
            if self.backend == "uia" and hasattr(w, "get_value"):
                out[name] = w.get_value() or ""
            else:
                out[name] = w.window_text() or ""
        return out

    def read(self) -> dict[str, float | None]:
        return {k: parse_number(v) for k, v in self.read_raw().items()}

    def close(self) -> None:
        try:
            self.win.close()
        except Exception as e:
            log.warning("TFMonitor 종료 실패: %r", e)

    def dump(self) -> str:
        lines = [f"{'kind':6} {'class':38} {'rect(l,t,r,b)':24} text"]
        for c in sorted(self.snapshot(), key=lambda c: (c.top, c.left)):
            cls = c.wrapper.class_name() if hasattr(c.wrapper, "class_name") else ""
            lines.append(f"{c.kind:6} {cls[:38]:38} {f'{c.left},{c.top},{c.right},{c.bottom}':24} {c.text!r}")
        return "\n".join(lines)


# --------------------------------------------------------------------------- logger thread
@dataclass
class TFMonitorSettings:
    exe_path: str | None = None
    title_re: str = DEFAULT_TITLE_RE
    backend: str = "win32"
    interval: float = 1.0
    click_start: bool = True
    click_stop: bool = True
    close_on_finish: bool = False  # 이 프로그램이 직접 실행한 경우에만 종료


ClientFactory = Callable[[TFMonitorSettings], Any]


def default_client_factory(s: TFMonitorSettings) -> TFMonitorClient:
    return TFMonitorClient(s.exe_path, s.title_re, s.backend)


class TFMonitorLogger(threading.Thread):
    """TFMonitor 값을 주기적으로 읽어 fan.csv 에 기록하는 스레드.

    pywinauto(특히 uia/COM) 객체는 생성한 스레드에서만 쓰도록 연결~종료를 모두 이 스레드에서 수행.
    """

    CSV_FIELDS = ["timestamp_iso", "epoch", "phase", *FIELDS]

    def __init__(self, settings: TFMonitorSettings, csv_path: Path, phase_getter: Callable[[], str],
                 on_sample: Callable[[dict], None] | None = None,
                 client_factory: ClientFactory = default_client_factory) -> None:
        super().__init__(daemon=True, name="TFMonitorLogger")
        self.s = settings
        self.csv_path = csv_path
        self.phase_getter = phase_getter
        self.on_sample = on_sample or (lambda row: None)
        self.client_factory = client_factory
        self.ready = threading.Event()
        self.error: BaseException | None = None
        self.samples = 0
        self._stop_evt = threading.Event()

    def start_and_wait(self, timeout: float = 90.0) -> None:
        """연결/Start 클릭/컨트롤 식별까지 완료될 때까지 대기. 실패 시 예외."""
        self.start()
        if not self.ready.wait(timeout):
            self._stop_evt.set()
            raise TFMonitorError(f"TFMonitor 준비 시간 초과 ({timeout:.0f}s)")
        if self.error:
            raise TFMonitorError(f"TFMonitor 연동 실패: {self.error}") from self.error

    def stop(self) -> None:
        self._stop_evt.set()
        self.join(timeout=15)

    def run(self) -> None:
        _com_init()
        client = None
        try:
            client = self.client_factory(self.s)
            client.connect(launch=True)
            if self.s.click_start:
                client.press("Start")
            client.resolve()
            log.info("TFMonitor 값 칸 매핑 완료: %s", ", ".join(FIELDS))
        except BaseException as e:
            self.error = e
            self.ready.set()
            return
        self.ready.set()

        fails = 0
        try:
            with self.csv_path.open("w", newline="", encoding="utf-8") as fp:
                w = csv.writer(fp)
                w.writerow(self.CSV_FIELDS)
                next_t = time.monotonic()
                while not self._stop_evt.is_set():
                    now = time.time()
                    try:
                        vals = client.read()
                        fails = 0
                    except Exception as e:
                        fails += 1
                        vals = dict.fromkeys(FIELDS)
                        if fails == 1:
                            log.warning("TFMonitor 값 읽기 실패: %r", e)
                        if fails % 5 == 0:  # 창 재생성 등 대비해 컨트롤 재탐색
                            try:
                                client.resolve()
                            except Exception:
                                pass
                    row = {"timestamp_iso": datetime.fromtimestamp(now).isoformat(timespec="milliseconds"),
                           "epoch": now, "phase": self.phase_getter(), **vals}
                    w.writerow([row["timestamp_iso"], f"{now:.3f}", row["phase"],
                                *("" if vals[k] is None else f"{vals[k]:g}" for k in FIELDS)])
                    fp.flush()
                    self.samples += 1
                    self.on_sample(row)
                    next_t += self.s.interval
                    self._stop_evt.wait(max(0.0, next_t - time.monotonic()))
        finally:
            try:
                if self.s.click_stop:
                    client.press("Stop")
                if self.s.close_on_finish and getattr(client, "launched", False):
                    client.close()
            except Exception as e:
                log.warning("TFMonitor 종료 처리 중 예외: %r", e)
            log.info("TFMonitor 로깅 종료 (%d samples) → %s", self.samples, self.csv_path)


def _com_init() -> None:
    if sys.platform == "win32":
        try:
            import comtypes
            comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
        except Exception:
            pass


# --------------------------------------------------------------------------- CLI 진단
def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="user_scenario.tfmonitor", description="TFMonitor 연동 진단")
    p.add_argument("--exe", help="TFMonitor.exe 경로 (창이 없을 때 실행)")
    p.add_argument("--title", default=DEFAULT_TITLE_RE, help="창 제목 정규식")
    p.add_argument("--backend", default="win32", choices=["win32", "uia"])
    p.add_argument("--dump", action="store_true", help="모든 컨트롤 출력")
    p.add_argument("--read", action="store_true", help="값 1회 읽기")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    c = TFMonitorClient(a.exe, a.title, a.backend)
    c.connect(launch=bool(a.exe))
    if a.dump or not a.read:
        print(c.dump())
    if a.read:
        raw = c.read_raw()
        for k, v in raw.items():
            print(f"{k:12} raw={v!r:12} → {parse_number(v)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
