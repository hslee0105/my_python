"""Phase 1: IDLE - 아무 입력/부하 없이 대기 (baseline 측정 구간)."""

from __future__ import annotations

import logging
import threading
import time

log = logging.getLogger("scenario.idle")


class IdlePhase:
    def __init__(self, seconds: float, stop_event: threading.Event | None = None) -> None:
        self.seconds = seconds
        self.stop = stop_event or threading.Event()

    def run(self) -> None:
        # busy-wait 없이 sleep 만 사용해 CPU wake-up 을 최소화 (C-state 진입 방해 X)
        # 로그 출력도 15초 간격으로만 수행
        end = time.monotonic() + self.seconds
        while (remain := end - time.monotonic()) > 0 and not self.stop.is_set():
            log.info("IDLE... 남은 시간 %.0fs", remain)
            self.stop.wait(min(15.0, remain))
