"""사용자 시나리오 자동화 러너.

  python -m user_scenario                       # IDLE 60s → 네이버 60s → YouTube 3개(각 60s)
  python -m user_scenario --browser msedge --video-seconds 0   # Edge, 영상 끝까지 재생
  python -m user_scenario --idle 300 --loops 3  # 시나리오 3회 반복

결과물 (results/<timestamp>/):
  phases.csv   : 페이즈별 시작/종료 시각 (외부 측정 로그와 align 용)
  resource.csv : CPU/Memory 주기 샘플 (psutil)
  youtube.csv  : 영상별 재생 시간, 해상도, total/dropped frames
  run.log      : 실행 로그
"""

from __future__ import annotations

import argparse
import csv
import logging
import random
import sys
from dataclasses import asdict, fields
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from .config import ScenarioConfig
from .phases import IdlePhase, NaverSurfingPhase, YouTubePhase
from .utils import PhaseRecorder, ResourceMonitor, keep_awake, setup_logging

log = logging.getLogger("scenario")


def parse_args(argv: list[str] | None = None) -> tuple[ScenarioConfig, int]:
    d = ScenarioConfig()
    p = argparse.ArgumentParser(prog="user_scenario", description="Laptop 사용자 시나리오 자동화")
    p.add_argument("--idle", type=float, default=d.idle_seconds, help="IDLE 시간 [s]")
    p.add_argument("--surf", type=float, default=d.surfing_seconds, help="웹서핑 시간 [s]")
    p.add_argument("--keywords", nargs="+", help="네이버 검색 키워드 풀 (기본: 내장 목록)")
    p.add_argument("--videos", nargs="+", help="YouTube URL 또는 검색어 목록 (기본: 내장 검색어)")
    p.add_argument("--video-count", type=int, default=d.video_count)
    p.add_argument("--video-seconds", type=float, default=d.video_seconds,
                   help="영상당 재생 시간 [s], 0 이면 끝까지")
    p.add_argument("--quality", default=d.video_quality,
                   choices=["auto", "tiny", "small", "medium", "large", "hd720", "hd1080", "hd1440", "hd2160"])
    p.add_argument("--mute", action="store_true")
    p.add_argument("--browser", dest="browser_channel", default=d.browser_channel,
                   help="msedge | chrome | (생략 시 Playwright Chromium)")
    p.add_argument("--browser-path", help="Chromium 계열 브라우저 실행 파일 경로 직접 지정")
    p.add_argument("--headless", action="store_true", help="헤드리스 (렌더링 부하가 달라지므로 측정 시 비권장)")
    p.add_argument("--out", type=Path, default=d.output_dir)
    p.add_argument("--interval", type=float, default=d.sample_interval, help="리소스 샘플링 주기 [s]")
    p.add_argument("--no-monitor", action="store_true")
    p.add_argument("--allow-sleep", action="store_true", help="화면/시스템 슬립 방지 해제")
    p.add_argument("--seed", type=int, help="키워드 랜덤 시드 (재현성)")
    p.add_argument("--loops", type=int, default=1, help="시나리오 반복 횟수")
    a = p.parse_args(argv)

    cfg = ScenarioConfig(
        idle_seconds=a.idle, surfing_seconds=a.surf,
        video_count=a.video_count, video_seconds=a.video_seconds, video_quality=a.quality,
        mute=a.mute, browser_channel=a.browser_channel, browser_path=a.browser_path,
        headless=a.headless,
        output_dir=a.out, sample_interval=a.interval, enable_monitor=not a.no_monitor,
        keep_awake=not a.allow_sleep, seed=a.seed,
    )
    if a.keywords:
        cfg.naver_keywords = a.keywords
    if a.videos:
        cfg.youtube_targets = a.videos
    return cfg, a.loops


def launch_context(pw, cfg: ScenarioConfig):
    w, h = cfg.window_size
    args = [
        "--autoplay-policy=no-user-gesture-required",
        "--disable-blink-features=AutomationControlled",
        "--start-maximized",
    ]
    browser = pw.chromium.launch(channel=cfg.browser_channel, executable_path=cfg.browser_path,
                                 headless=cfg.headless, args=args)
    # headed 모드에서는 실제 창(최대화) 크기를 그대로 사용
    view = {"viewport": {"width": w, "height": h}} if cfg.headless else {"no_viewport": True}
    context = browser.new_context(locale="ko-KR", timezone_id="Asia/Seoul", **view)
    context.set_default_timeout(15_000)
    return browser, context


def write_video_stats(path: Path, rows: list) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=["loop"] + [f.name for f in fields(rows[0][1])])
        w.writeheader()
        for loop, stat in rows:
            w.writerow({"loop": loop, **asdict(stat)})


def main(argv: list[str] | None = None) -> int:
    cfg, loops = parse_args(argv)
    out = cfg.output_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    setup_logging(out / "run.log")
    log.info("Config: %s, loops=%d", cfg, loops)
    log.info("결과 저장 경로: %s", out.resolve())

    rng = random.Random(cfg.seed)
    recorder = PhaseRecorder(out / "phases.csv")
    monitor = ResourceMonitor(out / "resource.csv", recorder, cfg.sample_interval) if cfg.enable_monitor else None
    video_rows: list = []

    if monitor:
        monitor.start()
    try:
        with keep_awake(cfg.keep_awake), sync_playwright() as pw:
            for loop in range(1, loops + 1):
                log.info("========== LOOP %d / %d ==========", loop, loops)

                # Phase 1: IDLE (브라우저 미실행 상태 = 순수 시스템 idle baseline)
                with recorder.phase("idle", f"loop{loop}"):
                    IdlePhase(cfg.idle_seconds).run()

                browser, context = launch_context(pw, cfg)
                try:
                    # Phase 2: 웹서핑
                    with recorder.phase("web_surfing", f"loop{loop}"):
                        NaverSurfingPhase(context, cfg.surfing_seconds, cfg.naver_keywords,
                                          cfg.dwell_range, cfg.click_result_prob, rng).run()

                    # Phase 3: YouTube (영상별 서브 페이즈 마커 기록)
                    with recorder.phase("youtube", f"loop{loop}"):
                        stats = YouTubePhase(
                            context, cfg.youtube_targets, cfg.video_count, cfg.video_seconds,
                            cfg.video_quality, cfg.mute, on_video=recorder.phase,
                        ).run()
                        video_rows += [(loop, s) for s in stats]
                finally:
                    context.close()
                    browser.close()
    except KeyboardInterrupt:
        log.warning("사용자 중단 (Ctrl+C)")
        return 130
    finally:
        if monitor:
            monitor.stop()
        recorder.close()
        write_video_stats(out / "youtube.csv", video_rows)
        log.info("시나리오 종료. 결과: %s", out.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
