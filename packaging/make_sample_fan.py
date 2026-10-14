"""CI 스모크 테스트용 합성 fan.csv / phases.csv 생성 (그래프 생성 경로 검증)."""

import csv
import math
import sys
from pathlib import Path

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
t0 = 1_790_000_000.0
plan = [("idle", 30), ("gap_idle", 10), ("web_surfing", 30), ("gap_idle", 10), ("youtube", 60)]
with (out / "phases.csv").open("w", newline="", encoding="utf-8") as fp:
    w = csv.writer(fp)
    w.writerow(["phase", "detail", "start_iso", "end_iso", "start_epoch", "end_epoch", "duration_s"])
    t = t0
    for name, dur in plan:
        w.writerow([name, "loop1", "", "", f"{t:.3f}", f"{t + dur:.3f}", dur])
        t += dur
with (out / "fan.csv").open("w", newline="", encoding="utf-8") as fp:
    w = csv.writer(fp)
    w.writerow(["timestamp_iso", "epoch", "phase", "fan0_rpm", "fan1_rpm", "cpu_temp_c"])
    for i in range(int(t - t0)):
        temp = 45 + 12 * math.sin(i / 25) ** 2
        rpm = 0 if temp < 48 else round(1800 + (temp - 48) * 150, -1)
        w.writerow(["", f"{t0 + i:.3f}", "", rpm, max(0, rpm - 80), round(temp)])
