"""시나리오 실행 엔진 (CLI / GUI 공용).

ScenarioConfig 로부터 실행 계획(Step 목록)을 만들고 순서대로 실행한다.
  - 시나리오 사이(반복 회차 사이 포함)에 gap_idle_seconds 만큼 IDLE 구간 삽입
  - stop_event 로 언제든 중단 가능 (진행 중인 Playwright 호출은 timeout 내에 반환)
  - on_event 콜백으로 진행 상황 통지 (GUI 표시용)
"""

from __future__ import annotations

import csv
import logging
import random
import threading
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from playwright.sync_api import sync_playwright

from .config import BROWSER_SCENARIOS, SCENARIOS, ScenarioConfig
from .phases import IdlePhase, NaverSurfingPhase, YouTubePhase
from .utils import (PhaseRecorder, ResourceMonitor, add_log_handler, keep_awake,
                    remove_log_handler)

log = logging.getLogger("scenario")

EventCallback = Callable[[dict[str, Any]], None]


@dataclass
class Step:
    kind: str  # idle | web_surfing | youtube | gap_idle
    loop: int
    planned_s: float | None  # None = 소요 시간 미정 (영상 끝까지 재생)

    @property
    def label(self) -> str:
        name = "간격 IDLE" if self.kind == "gap_idle" else SCENARIOS[self.kind]
        return f"[Loop {self.loop}] {name}"


def build_plan(cfg: ScenarioConfig) -> list[Step]:
    steps: list[Step] = []
    for loop in range(1, cfg.loops + 1):
        for kind in cfg.scenarios:
            if steps and cfg.gap_idle_seconds > 0:
                steps.append(Step("gap_idle", loop, cfg.gap_idle_seconds))
            steps.append(Step(kind, loop, cfg.planned_seconds(kind)))
    return steps


def planned_total(steps: list[Step]) -> float | None:
    if any(s.planned_s is None for s in steps):
        return None
    return sum(s.planned_s for s in steps)


class _Browser:
    """필요할 때만 브라우저를 띄우고, IDLE 구간에서는 닫는다."""

    def __init__(self, pw, cfg: ScenarioConfig) -> None:
        self.pw, self.cfg = pw, cfg
        self.browser = self.context = None

    def ensure(self):
        if self.context is None:
            cfg = self.cfg
            log.info("브라우저 실행 (channel=%s)", cfg.browser_channel or "playwright-chromium")
            args = ["--autoplay-policy=no-user-gesture-required",
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized"]
            self.browser = self.pw.chromium.launch(
                channel=cfg.browser_channel, executable_path=cfg.browser_path,
                headless=cfg.headless, args=args)
            # headed 모드에서는 실제 창(최대화) 크기를 그대로 사용
            w, h = cfg.window_size
            view = {"viewport": {"width": w, "height": h}} if cfg.headless else {"no_viewport": True}
            self.context = self.browser.new_context(locale="ko-KR", timezone_id="Asia/Seoul", **view)
            self.context.set_default_timeout(15_000)
        return self.context

    def close(self) -> None:
        if self.browser is not None:
            log.info("브라우저 종료")
            try:
                self.context.close()
                self.browser.close()
            except Exception as e:
                log.warning("브라우저 종료 중 예외: %r", e)
        self.browser = self.context = None


def _write_video_stats(path: Path, rows: list) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=["loop"] + [f.name for f in fields(rows[0][1])])
        w.writeheader()
        for loop, stat in rows:
            w.writerow({"loop": loop, **asdict(stat)})


def _start_tfmonitor(cfg: ScenarioConfig, out: Path, recorder: PhaseRecorder, emit: EventCallback,
                     client_factory=None):
    from .tfmonitor import TFMonitorLogger, TFMonitorSettings, default_client_factory

    settings = TFMonitorSettings(
        exe_path=cfg.tfmon_exe, title_re=cfg.tfmon_title_re, backend=cfg.tfmon_backend,
        interval=cfg.tfmon_interval, click_stop=cfg.tfmon_click_stop, close_on_finish=cfg.tfmon_close,
        require_admin=cfg.tfmon_require_admin)
    logger = TFMonitorLogger(settings, out / "fan.csv", lambda: recorder.current,
                             on_sample=lambda row: emit({"event": "fan", **row}),
                             client_factory=client_factory or default_client_factory)
    log.info("TFMonitor 연동 시작 (Start 클릭 → FAN/온도 로깅)")
    logger.start_and_wait()
    return logger


def _run_fan_analysis(out: Path, emit: EventCallback) -> None:
    try:
        from .fan_analysis import analyze
        paths = analyze(out)
        log.info("FAN/온도 분석 완료: %s", ", ".join(p.name for p in paths if p.parent == out))
        emit({"event": "analysis", "paths": paths})
    except Exception as e:
        log.warning("FAN/온도 분석 실패: %r", e)


def run_scenario(cfg: ScenarioConfig, stop_event: threading.Event | None = None,
                 on_event: EventCallback | None = None, tfmon_client_factory=None) -> Path:
    """시나리오 실행. 결과 디렉터리 경로를 반환."""
    stop = stop_event or threading.Event()
    emit = on_event or (lambda e: None)
    steps = build_plan(cfg)
    if not steps:
        raise ValueError("선택된 시나리오가 없습니다")

    out = cfg.output_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    file_handler = add_log_handler(logging.FileHandler(out / "run.log", encoding="utf-8"))
    log.info("Config: %s", cfg)
    log.info("실행 계획 (%d steps): %s", len(steps), " → ".join(s.label for s in steps))
    log.info("결과 저장 경로: %s", out.resolve())
    emit({"event": "start", "out": out, "steps": steps, "planned_total": planned_total(steps)})

    rng = random.Random(cfg.seed)
    recorder = PhaseRecorder(out / "phases.csv")
    monitor = ResourceMonitor(out / "resource.csv", recorder, cfg.sample_interval) if cfg.enable_monitor else None
    video_rows: list = []
    error: BaseException | None = None
    tf_logger = None

    if monitor:
        monitor.start()
    try:
        if cfg.tfmon_enabled:
            # 연결 실패 시 시나리오를 시작하지 않음 (FAN 데이터 없는 측정 방지)
            tf_logger = _start_tfmonitor(cfg, out, recorder, emit, tfmon_client_factory)
        with keep_awake(cfg.keep_awake), sync_playwright() as pw:
            browser = _Browser(pw, cfg)
            try:
                for i, step in enumerate(steps):
                    if stop.is_set():
                        break
                    if step.kind in BROWSER_SCENARIOS:
                        context = browser.ensure()  # 브라우저 기동은 페이즈 마커 밖에서 수행
                    elif cfg.close_browser_on_idle:
                        browser.close()

                    emit({"event": "step", "index": i, "step": step})
                    with recorder.phase(step.kind, f"loop{step.loop}"):
                        if step.kind in ("idle", "gap_idle"):
                            IdlePhase(step.planned_s, stop).run()
                        elif step.kind == "web_surfing":
                            NaverSurfingPhase(context, cfg.surfing_seconds, cfg.naver_keywords,
                                              cfg.dwell_range, cfg.click_result_prob, rng, stop).run()
                        elif step.kind == "youtube":
                            stats = YouTubePhase(
                                context, cfg.youtube_targets, cfg.video_count, cfg.video_seconds,
                                cfg.video_quality, cfg.mute, on_video=recorder.phase, stop_event=stop,
                            ).run()
                            video_rows += [(step.loop, s) for s in stats]
            finally:
                browser.close()
    except BaseException as e:  # KeyboardInterrupt 포함 - 결과 파일은 항상 정리
        error = e
        raise
    finally:
        if tf_logger:
            tf_logger.stop()
        if monitor:
            monitor.stop()
        recorder.close()
        _write_video_stats(out / "youtube.csv", video_rows)
        if tf_logger and tf_logger.samples:
            _run_fan_analysis(out, emit)
        if stop.is_set():
            log.warning("사용자 요청으로 시나리오 중단")
        log.info("시나리오 종료. 결과: %s", out.resolve())
        remove_log_handler(file_handler)
        emit({"event": "done", "out": out, "stopped": stop.is_set(),
              "error": None if error is None else repr(error)})
    return out
