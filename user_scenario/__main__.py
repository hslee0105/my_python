"""사용자 시나리오 자동화 CLI.

  python -m user_scenario                       # IDLE 60s → 네이버 60s → YouTube 3개(각 60s)
  python -m user_scenario --gui                 # GUI Controller 실행
  python -m user_scenario --scenarios web_surfing youtube --gap 30   # 시나리오 사이 IDLE 30s
  python -m user_scenario --browser msedge --video-seconds 0         # Edge, 영상 끝까지 재생
  python -m user_scenario --elevate --tfmon --tfmon-exe "C:\\Tools\\TFMonitor\\TFMonitor.exe"   # FAN/온도 로깅

결과물 (results/<timestamp>/):
  phases.csv   : 페이즈별 시작/종료 시각 (외부 측정 로그와 align 용)
  resource.csv : CPU/Memory 주기 샘플 (psutil)
  youtube.csv  : 영상별 재생 시간, 해상도, total/dropped frames
  run.log      : 실행 로그
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import QUALITIES, SCENARIOS, ScenarioConfig
from .utils import add_log_handler, is_admin, relaunch_as_admin


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    d = ScenarioConfig()
    p = argparse.ArgumentParser(prog="user_scenario", description="Laptop 사용자 시나리오 자동화")
    p.add_argument("--gui", action="store_true", help="GUI Controller 실행")
    p.add_argument("--scenarios", nargs="+", choices=list(SCENARIOS), default=d.scenarios,
                   help="실행할 시나리오와 순서")
    p.add_argument("--gap", type=float, default=d.gap_idle_seconds, help="시나리오 사이 IDLE 시간 [s]")
    p.add_argument("--loops", type=int, default=d.loops, help="시나리오 반복 횟수")
    p.add_argument("--keep-browser", action="store_true", help="IDLE 구간에서도 브라우저를 닫지 않음")
    p.add_argument("--idle", type=float, default=d.idle_seconds, help="IDLE 시나리오 시간 [s]")
    p.add_argument("--surf", type=float, default=d.surfing_seconds, help="웹서핑 시간 [s]")
    p.add_argument("--keywords", nargs="+", help="네이버 검색 키워드 풀 (기본: 내장 목록)")
    p.add_argument("--videos", nargs="+", help="YouTube URL 또는 검색어 목록 (기본: 내장 검색어)")
    p.add_argument("--video-count", type=int, default=d.video_count)
    p.add_argument("--video-seconds", type=float, default=d.video_seconds,
                   help="영상당 재생 시간 [s], 0 이면 끝까지")
    p.add_argument("--quality", default=d.video_quality, choices=QUALITIES)
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
    g = p.add_argument_group("TFMonitor 연동 (FAN RPM / CPU 온도 로깅, Windows)")
    g.add_argument("--tfmon", action="store_true", help="TFMonitor 연동 활성화")
    g.add_argument("--tfmon-exe", help="TFMonitor.exe 경로 (창이 없으면 실행)")
    g.add_argument("--tfmon-title", default=d.tfmon_title_re, help="TFMonitor 창 제목 정규식")
    g.add_argument("--tfmon-backend", default=d.tfmon_backend, choices=["win32", "uia"])
    g.add_argument("--tfmon-interval", type=float, default=d.tfmon_interval, help="샘플링 주기 [s]")
    g.add_argument("--tfmon-no-stop", action="store_true", help="종료 시 [Stop] 클릭 안 함")
    g.add_argument("--tfmon-close", action="store_true", help="직접 실행한 TFMonitor 를 종료 시 닫기")
    g.add_argument("--tfmon-no-admin", action="store_true",
                   help="관리자 권한 확인 생략 (TFMonitor 가 일반 권한으로 동작하는 경우만)")
    p.add_argument("--elevate", action="store_true", help="관리자 권한이 아니면 UAC 로 관리자 권한 재실행")
    p.add_argument("--pause", action="store_true", help=argparse.SUPPRESS)  # 재실행 창이 바로 닫히지 않도록
    return p.parse_args(argv)


def config_from_args(a: argparse.Namespace) -> ScenarioConfig:
    cfg = ScenarioConfig(
        scenarios=a.scenarios, gap_idle_seconds=a.gap, loops=a.loops,
        close_browser_on_idle=not a.keep_browser,
        idle_seconds=a.idle, surfing_seconds=a.surf,
        video_count=a.video_count, video_seconds=a.video_seconds, video_quality=a.quality,
        mute=a.mute, browser_channel=a.browser_channel, browser_path=a.browser_path,
        headless=a.headless, output_dir=a.out, sample_interval=a.interval,
        enable_monitor=not a.no_monitor, keep_awake=not a.allow_sleep, seed=a.seed,
        tfmon_enabled=a.tfmon, tfmon_exe=a.tfmon_exe, tfmon_title_re=a.tfmon_title,
        tfmon_backend=a.tfmon_backend, tfmon_interval=a.tfmon_interval,
        tfmon_click_stop=not a.tfmon_no_stop, tfmon_close=a.tfmon_close,
        tfmon_require_admin=not a.tfmon_no_admin,
    )
    if a.keywords:
        cfg.naver_keywords = a.keywords
    if a.videos:
        cfg.youtube_targets = a.videos
    return cfg


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    a = parse_args(argv)
    needs_admin = a.gui or (a.tfmon and not a.tfmon_no_admin)
    if a.elevate and needs_admin and not is_admin():
        args = ["-m", "user_scenario", *[x for x in argv if x != "--elevate"]]
        try:
            relaunch_as_admin(args if a.gui else [*args, "--pause"])
        except OSError as e:
            print(e)
            return 1
        print("관리자 권한 창에서 다시 실행합니다.")
        return 0
    if a.gui:
        from .gui import main as gui_main
        return gui_main()

    from .runner import run_scenario
    from .tfmonitor import TFMonitorError

    add_log_handler(logging.StreamHandler(sys.stdout))
    try:
        run_scenario(config_from_args(a))
    except KeyboardInterrupt:
        logging.getLogger("scenario").warning("사용자 중단 (Ctrl+C)")
        return 130
    except TFMonitorError as e:
        logging.getLogger("scenario").error("%s → 시나리오를 시작하지 않았습니다", e)
        if not is_admin():
            print("\n  → 'python -m user_scenario --elevate ...' 로 관리자 권한 재실행할 수 있습니다.")
        return 1
    finally:
        if a.pause:
            input("\nEnter 키를 누르면 창이 닫힙니다...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
