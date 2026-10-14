"""공통 유틸: 로깅, 페이즈 마커, 시스템 리소스 샘플러, 화면 꺼짐 방지."""

from __future__ import annotations

import csv
import ctypes
import logging
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

try:
    import psutil
except ImportError:  # psutil 없이도 시나리오는 동작
    psutil = None

log = logging.getLogger("scenario")


def setup_logging(log_path: Path) -> None:
    fmt = logging.Formatter("%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s", "%H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in (logging.StreamHandler(sys.stdout), logging.FileHandler(log_path, encoding="utf-8")):
        handler.setFormatter(fmt)
        root.addHandler(handler)


class PhaseRecorder:
    """페이즈별 시작/종료 시각을 CSV로 기록.

    외부 측정 장비(Power meter, PresentMon, GPU-Z, HWiNFO 등) 로그와
    타임스탬프로 정렬(align)할 수 있도록 wall-clock(ISO8601)과 epoch 둘 다 남긴다.
    """

    FIELDS = ["phase", "detail", "start_iso", "end_iso", "start_epoch", "end_epoch", "duration_s"]

    def __init__(self, path: Path) -> None:
        self.path = path
        self._fp = path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._fp, fieldnames=self.FIELDS)
        self._writer.writeheader()
        self.current = "init"

    @contextmanager
    def phase(self, name: str, detail: str = "") -> Iterator[None]:
        prev, self.current = self.current, name
        t0 = time.time()
        log.info("▶ PHASE START: %s %s", name, detail)
        try:
            yield
        finally:
            t1 = time.time()
            self._writer.writerow({
                "phase": name,
                "detail": detail,
                "start_iso": datetime.fromtimestamp(t0).isoformat(timespec="milliseconds"),
                "end_iso": datetime.fromtimestamp(t1).isoformat(timespec="milliseconds"),
                "start_epoch": f"{t0:.3f}",
                "end_epoch": f"{t1:.3f}",
                "duration_s": f"{t1 - t0:.3f}",
            })
            self._fp.flush()
            log.info("■ PHASE END  : %s (%.1fs)", name, t1 - t0)
            self.current = prev

    def close(self) -> None:
        self._fp.close()


class ResourceMonitor(threading.Thread):
    """psutil 기반 주기 샘플러 (CPU util/freq, Memory, 현재 페이즈)."""

    def __init__(self, path: Path, recorder: PhaseRecorder, interval: float = 1.0) -> None:
        super().__init__(daemon=True, name="ResourceMonitor")
        self.path = path
        self.recorder = recorder
        self.interval = interval
        self._stop_evt = threading.Event()

    def run(self) -> None:
        if psutil is None:
            log.warning("psutil 미설치 - 리소스 모니터링 비활성화")
            return
        n_cpu = psutil.cpu_count(logical=True)
        with self.path.open("w", newline="", encoding="utf-8") as fp:
            w = csv.writer(fp)
            w.writerow(["timestamp_iso", "epoch", "phase", "cpu_total_pct", "cpu_max_core_pct",
                        "cpu_freq_mhz", "mem_used_pct", "mem_used_mb"]
                       + [f"cpu{i}_pct" for i in range(n_cpu)])
            psutil.cpu_percent(percpu=True)  # 첫 호출은 기준점 설정용
            next_t = time.monotonic()
            while not self._stop_evt.is_set():
                next_t += self.interval
                self._stop_evt.wait(max(0.0, next_t - time.monotonic()))
                per_core = psutil.cpu_percent(percpu=True)
                freq = psutil.cpu_freq()
                vm = psutil.virtual_memory()
                now = time.time()
                w.writerow([
                    datetime.fromtimestamp(now).isoformat(timespec="milliseconds"),
                    f"{now:.3f}",
                    self.recorder.current,
                    f"{sum(per_core) / len(per_core):.1f}",
                    f"{max(per_core):.1f}",
                    f"{freq.current:.0f}" if freq else "",
                    f"{vm.percent:.1f}",
                    f"{vm.used / 2**20:.0f}",
                    *[f"{c:.1f}" for c in per_core],
                ])
                fp.flush()

    def stop(self) -> None:
        self._stop_evt.set()
        self.join(timeout=5)


# Windows: SetThreadExecutionState 로 측정 중 디스플레이/시스템 슬립 방지
_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001
_ES_DISPLAY_REQUIRED = 0x00000002


@contextmanager
def keep_awake(enabled: bool = True) -> Iterator[None]:
    if not (enabled and sys.platform == "win32"):
        yield
        return
    kernel32 = ctypes.windll.kernel32
    kernel32.SetThreadExecutionState(_ES_CONTINUOUS | _ES_SYSTEM_REQUIRED | _ES_DISPLAY_REQUIRED)
    log.info("Display/System sleep 방지 활성화")
    try:
        yield
    finally:
        kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
