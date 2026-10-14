"""FAN RPM / CPU 온도 시나리오별 분석 및 그래프 생성.

입력 (결과 폴더):  fan.csv (TFMonitor 로그), phases.csv (페이즈 시작/종료)
출력:
  fan_timeline.png            전체 시간축 꺾은선 (상: FAN0/FAN1 RPM, 하: CPU 온도), 페이즈 구간 음영
  fan_phases/NN_<phase>_loopK.png   페이즈(시나리오 실행 1회)별 꺾은선 (x = 페이즈 시작 후 경과 시간)
  fan_summary.png             시나리오 종류별 평균/최대 RPM, 평균/최대 온도 비교
  fan_summary.csv             페이즈 1회 단위 통계
  fan_summary_by_scenario.csv 시나리오 종류별 집계 통계

샘플→페이즈 매핑은 epoch 기준으로 phases.csv 구간에 넣어 계산한다 (로깅 스레드의 태그와 무관).

  python -m user_scenario.fan_analysis results/20261014_120000
"""

from __future__ import annotations

import csv
import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from matplotlib import font_manager, rcParams
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

log = logging.getLogger("scenario.fan")

TOP_PHASES = ("idle", "gap_idle", "web_surfing", "youtube")
PHASE_LABEL = {"idle": "IDLE", "gap_idle": "간격 IDLE", "web_surfing": "웹서핑", "youtube": "YouTube"}

# 고정 순서 categorical 팔레트 (series 1, 2, 3) - 색은 엔티티를 따라감
FANS = [("fan0_rpm", "FAN 0", "#2a78d6"), ("fan1_rpm", "FAN 1", "#eb6834")]
TEMP = ("cpu_temp_c", "CPU 온도 (C0)", "#1baf7a")
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SHADE = ("#f4f4f2", "#e9e8e4")  # 페이즈 구간 교대 음영 (중립 회색)


def _setup_fonts() -> None:
    names = {f.name for f in font_manager.fontManager.ttflist}
    for cand in ("Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR", "Noto Sans KR"):
        if cand in names:
            rcParams["font.family"] = cand
            break
    rcParams["axes.unicode_minus"] = False
    rcParams.update({
        "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "axes.titlecolor": INK, "axes.spines.top": False, "axes.spines.right": False,
        "grid.color": GRID, "grid.linewidth": 0.8, "legend.frameon": False, "font.size": 9,
    })


@dataclass
class Span:
    index: int
    kind: str
    loop: str
    start: float
    end: float

    @property
    def label(self) -> str:
        return PHASE_LABEL.get(self.kind, self.kind)


@dataclass
class Samples:
    epoch: np.ndarray
    values: dict[str, np.ndarray]  # 결측 = nan

    def slice(self, start: float, end: float) -> "Samples":
        m = (self.epoch >= start) & (self.epoch < end)
        return Samples(self.epoch[m], {k: v[m] for k, v in self.values.items()})


def load_samples(path: Path) -> Samples:
    cols = [k for k, *_ in FANS] + [TEMP[0]]
    ep, vals = [], {k: [] for k in cols}
    with path.open(encoding="utf-8") as fp:
        for row in csv.DictReader(fp):
            ep.append(float(row["epoch"]))
            for k in cols:
                v = row.get(k, "")
                vals[k].append(float(v) if v not in ("", None) else math.nan)
    return Samples(np.array(ep), {k: np.array(v, dtype=float) for k, v in vals.items()})


def load_spans(path: Path) -> list[Span]:
    spans = []
    with path.open(encoding="utf-8") as fp:
        for row in csv.DictReader(fp):
            if row["phase"] in TOP_PHASES:
                spans.append(Span(0, row["phase"], row["detail"], float(row["start_epoch"]), float(row["end_epoch"])))
    spans.sort(key=lambda s: s.start)
    for i, s in enumerate(spans, 1):
        s.index = i
    return spans


# --------------------------------------------------------------------------- 통계
def _stats(v: np.ndarray, prefix: str, fan: bool) -> dict[str, float | int | str]:
    v = v[~np.isnan(v)]
    if v.size == 0:
        return {}
    d: dict[str, float | int | str] = {
        f"{prefix}_avg": round(float(v.mean()), 1), f"{prefix}_min": float(v.min()),
        f"{prefix}_max": float(v.max()), f"{prefix}_p95": round(float(np.percentile(v, 95)), 1),
        f"{prefix}_std": round(float(v.std()), 1),
        f"{prefix}_start": float(v[0]), f"{prefix}_end": float(v[-1]),
    }
    if fan:
        d[f"{prefix}_on_ratio_pct"] = round(100 * float((v > 0).mean()), 1)  # 팬 동작 비율
        d[f"{prefix}_level_changes"] = int(np.count_nonzero(np.diff(v) != 0))  # RPM 변동 횟수 (hunting 지표)
    else:
        d[f"{prefix}_delta"] = round(float(v[-1] - v[0]), 1)  # 페이즈 동안 온도 변화
    return d


def span_stats(span: Span, s: Samples) -> dict:
    part = s.slice(span.start, span.end)
    row = {"index": span.index, "scenario": span.kind, "loop": span.loop,
           "duration_s": round(span.end - span.start, 1), "samples": int(part.epoch.size)}
    for key, *_ in FANS:
        row.update(_stats(part.values[key], key, fan=True))
    row.update(_stats(part.values[TEMP[0]], TEMP[0], fan=False))
    return row


def scenario_stats(spans: list[Span], s: Samples) -> list[dict]:
    """시나리오 종류별 집계 (모든 회차 샘플 합산)."""
    rows = []
    for kind in TOP_PHASES:
        mine = [sp for sp in spans if sp.kind == kind]
        if not mine:
            continue
        parts = [s.slice(sp.start, sp.end) for sp in mine]
        merged = Samples(np.concatenate([p.epoch for p in parts]),
                         {k: np.concatenate([p.values[k] for p in parts]) for k in s.values})
        row = {"scenario": kind, "runs": len(mine),
               "duration_s": round(sum(sp.end - sp.start for sp in mine), 1), "samples": int(merged.epoch.size)}
        for key, *_ in FANS:
            row.update({k: v for k, v in _stats(merged.values[key], key, fan=True).items()
                        if not k.endswith(("_start", "_end"))})
        row.update({k: v for k, v in _stats(merged.values[TEMP[0]], TEMP[0], fan=False).items()
                    if not k.endswith(("_start", "_end", "_delta"))})
        rows.append(row)
    return rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys: list[str] = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with path.open("w", newline="", encoding="utf-8-sig") as fp:  # utf-8-sig: Excel 한글 깨짐 방지
        w = csv.DictWriter(fp, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


# --------------------------------------------------------------------------- 그래프
def _mmss(x: float, _pos=None) -> str:
    x = int(round(x))
    return f"{x // 60}:{x % 60:02d}" if x < 3600 else f"{x // 3600}:{x % 3600 // 60:02d}:{x % 60:02d}"


def _line_axes(title: str, width: float = 12.0) -> tuple[Figure, tuple]:
    fig = Figure(figsize=(width, 6.2), dpi=120, layout="constrained")
    ax_rpm, ax_t = fig.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [1.15, 1]})
    fig.suptitle(title, color=INK, fontsize=12, fontweight="bold", x=0.01, ha="left")
    for ax in (ax_rpm, ax_t):
        ax.grid(axis="y")
        ax.tick_params(length=0)
    ax_rpm.set_ylabel("FAN 속도 (RPM)")
    ax_t.set_ylabel("CPU 온도 (°C)")
    ax_t.set_xlabel("경과 시간 (m:ss)")
    ax_t.xaxis.set_major_formatter(FuncFormatter(_mmss))
    return fig, (ax_rpm, ax_t)


def _plot_series(ax_rpm, ax_t, x: np.ndarray, s: Samples) -> None:
    for key, name, color in FANS:
        ax_rpm.plot(x, s.values[key], color=color, lw=1.8, label=name)
    key, name, color = TEMP
    ax_t.plot(x, s.values[key], color=color, lw=1.8, label=name)
    ax_rpm.legend(loc="upper left", ncols=2, fontsize=8)
    ax_rpm.set_ylim(bottom=0)


def plot_timeline(spans: list[Span], s: Samples, path: Path, title: str) -> None:
    t0 = spans[0].start if spans else s.epoch[0]
    total = (max(spans[-1].end, s.epoch[-1]) if spans else s.epoch[-1]) - t0
    fig, (ax_rpm, ax_t) = _line_axes(title, width=min(24.0, max(12.0, total / 60)))
    for i, sp in enumerate(spans):
        for ax in (ax_rpm, ax_t):
            ax.axvspan(sp.start - t0, sp.end - t0, color=SHADE[i % 2], lw=0, zorder=0)
        ax_rpm.text((sp.start + sp.end) / 2 - t0, 1.01, sp.label, transform=ax_rpm.get_xaxis_transform(),
                    ha="center", va="bottom", fontsize=8, color=INK2, clip_on=False)
    _plot_series(ax_rpm, ax_t, s.epoch - t0, s)
    ax_t.set_xlim(left=min(0.0, float(s.epoch[0] - t0)))
    fig.savefig(path)


def plot_span(span: Span, s: Samples, path: Path) -> None:
    part = s.slice(span.start, span.end)
    fig, (ax_rpm, ax_t) = _line_axes(f"{span.index:02d}. {span.label} ({span.loop}) - FAN 속도 / CPU 온도", 10.0)
    if part.epoch.size:
        _plot_series(ax_rpm, ax_t, part.epoch - span.start, part)
    ax_t.set_xlim(0, span.end - span.start)
    fig.savefig(path)


def _avg_max_bars(ax, xs, rows, key, label, color, width, fmt) -> None:
    avg = np.array([r.get(f"{key}_avg", np.nan) for r in rows], dtype=float)
    mx = np.array([r.get(f"{key}_max", np.nan) for r in rows], dtype=float)
    ax.bar(xs, avg, width, color=color, label=label)
    ax.vlines(xs, avg, mx, color=INK2, lw=1)
    ax.scatter(xs, mx, s=30, color=color, edgecolor="white", linewidth=1.5, zorder=3)
    for xi, a, m in zip(xs, avg, mx):
        if np.isfinite(a):
            ax.annotate(f"{fmt.format(a)}\n(max {fmt.format(m)})", (xi, m), xytext=(0, 5),
                        textcoords="offset points", ha="center", va="bottom", fontsize=7.5, color=INK2)


def plot_summary(rows: list[dict], path: Path) -> None:
    fig = Figure(figsize=(10, 6.2), dpi=120, layout="constrained")
    ax_rpm, ax_t = fig.subplots(2, 1)
    fig.suptitle("시나리오별 FAN 속도 / CPU 온도 (막대 = 평균, 선 끝 점 = 최대)", color=INK, fontsize=12,
                 fontweight="bold", x=0.01, ha="left")
    labels = [PHASE_LABEL.get(r["scenario"], r["scenario"]) for r in rows]
    x = np.arange(len(rows))
    w = 0.34
    for j, (key, name, color) in enumerate(FANS):
        _avg_max_bars(ax_rpm, x + (j - 0.5) * (w + 0.02), rows, key, f"{name} 평균", color, w, "{:.0f}")
    key, name, color = TEMP
    _avg_max_bars(ax_t, x, rows, key, f"{name} 평균", color, 0.5, "{:.1f}")
    for ax, ylabel in ((ax_rpm, "RPM"), (ax_t, "°C")):
        ax.set_xticks(x, labels)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y")
        ax.set_axisbelow(True)
        ax.tick_params(length=0)
        ax.legend(loc="upper left", fontsize=8, ncols=2)
        ax.margins(y=0.3)
    fig.savefig(path)


# --------------------------------------------------------------------------- entry
def analyze(out_dir: Path) -> list[Path]:
    out_dir = Path(out_dir)
    fan_csv, phases_csv = out_dir / "fan.csv", out_dir / "phases.csv"
    if not fan_csv.exists():
        raise FileNotFoundError(fan_csv)
    s = load_samples(fan_csv)
    if s.epoch.size == 0:
        raise ValueError("fan.csv 에 샘플이 없습니다")
    spans = load_spans(phases_csv) if phases_csv.exists() else []
    _setup_fonts()

    outputs: list[Path] = []
    p = out_dir / "fan_timeline.png"
    plot_timeline(spans, s, p, f"FAN 속도 / CPU 온도 - 전체 시나리오 ({out_dir.name})")
    outputs.append(p)

    per_span = [span_stats(sp, s) for sp in spans]
    by_kind = scenario_stats(spans, s)
    _write_csv(out_dir / "fan_summary.csv", per_span)
    _write_csv(out_dir / "fan_summary_by_scenario.csv", by_kind)
    outputs += [out_dir / "fan_summary.csv", out_dir / "fan_summary_by_scenario.csv"]

    if spans:
        sub = out_dir / "fan_phases"
        sub.mkdir(exist_ok=True)
        for sp in spans:
            p = sub / f"{sp.index:02d}_{sp.kind}_{sp.loop}.png"
            plot_span(sp, s, p)
            outputs.append(p)
    if by_kind:
        p = out_dir / "fan_summary.png"
        plot_summary(by_kind, p)
        outputs.append(p)

    for r in by_kind:
        log.info("[FAN] %-11s FAN0 avg %s / max %s rpm · FAN1 avg %s / max %s rpm · CPU avg %s / max %s °C",
                 r["scenario"], r.get("fan0_rpm_avg"), r.get("fan0_rpm_max"), r.get("fan1_rpm_avg"),
                 r.get("fan1_rpm_max"), r.get("cpu_temp_c_avg"), r.get("cpu_temp_c_max"))
    return outputs


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: python -m user_scenario.fan_analysis <결과 폴더> [...]")
        return 2
    for d in args:
        for p in analyze(Path(d)):
            print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
