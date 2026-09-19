"""Turn one run of the SHM model into the panels the app draws beside the number.

``predict`` answers how much fatigue damage a file carries; this answers why that
much, which is the part a non-technical reader can actually check. Every quantity
comes straight off Miner's rule as the Info Kit states it — damage accumulates
from zero and failure is reached at D >= 1 (§1.3.1) — so nothing here invents a
severity band the organisers never defined.

Panels are plain dicts, not a type of ours, so the app can draw them without
importing this subsystem. The shapes are documented in ``src/app/services.py``.
"""

import math
from pathlib import Path

import numpy as np

from .config import (
    CONCENTRATION_BANDS,
    FAILURE_DAMAGE,
    RECOMMENDATIONS,
    RECOMMENDATION_SCOPE,
    RUNS_REMAINING_ALERT,
    SEVERITY_CAUTION,
    SEVERITY_CLEAR,
    SEVERITY_DANGER,
    TRACE_TARGET_POINTS,
)
from .dataset import read_stress_series
from .features import cycle_damage, extract_cycles
from .model import DamageModel
from .predict import load_model

VERDICT_HEADLINE = "{damage:.0%} of fatigue life used"
VERDICT_DETAIL = "Room for {runs} more runs like this one. Worst of {count} files."
RUNS_UNLIMITED = "No limit"

BULLET_TITLE = "Fatigue life used"
BULLET_CAPTION = "Fatigue life runs out at 1.00. The gap to the marker is what is left."
TARGET_LABEL = "End of life (D = 1.00)"

METRICS_TITLE = "Worst file"
METRICS_CAPTION = "Damage adds up run by run, so this counts the runs still left."

BANDS_TITLE = "Where the damage comes from"
BANDS_CAPTION = (
    "Cycles sorted by damage, in groups that do not overlap, so the shares total "
    "100%. A few large cycles do nearly all of it."
)
BANDS_VALUE_TITLE = "Share of total damage"

TRACE_TITLE = "Stress history"
TRACE_CAPTION = "Highest and lowest reading per window. Peaks are kept, not averaged away."
TRACE_X_TITLE = "Sample"
# The Info Kit documents neither the stress unit nor the sampling rate, so the axes
# say what is actually known instead of implying MPa and seconds.
TRACE_Y_TITLE = "Stress (as recorded)"


def _envelope(series: np.ndarray, target_points: int) -> tuple[list[int], list[float]]:
    """Reduce a long history to a drawable min/max envelope, extremes intact."""
    if series.size <= target_points:
        return list(range(series.size)), [float(value) for value in series]

    buckets = target_points // 2
    usable = (series.size // buckets) * buckets
    blocks = series[:usable].reshape(buckets, -1)
    positions = np.arange(usable).reshape(buckets, -1)

    rows = np.arange(buckets)
    lowest = blocks.argmin(axis=1)
    highest = blocks.argmax(axis=1)
    # Emit each bucket's pair in the order they occur, or the line doubles back on
    # itself and draws a saw that is not in the data.
    first = np.minimum(lowest, highest)
    second = np.maximum(lowest, highest)

    x = np.stack([positions[rows, first], positions[rows, second]], axis=1).ravel()
    y = np.stack([blocks[rows, first], blocks[rows, second]], axis=1).ravel()

    if usable < series.size:
        x = np.append(x, series.size - 1)
        y = np.append(y, series[-1])
    return x.tolist(), y.tolist()


def _concentration(damage: np.ndarray) -> list[dict]:
    """Share of total damage held by each disjoint slice of the sorted cycles."""
    total = float(damage.sum())
    if damage.size == 0 or total <= 0:
        return []

    ordered = np.sort(damage)[::-1]
    cumulative = np.cumsum(ordered)

    rows: list[dict] = []
    start = 0
    for edge, label in CONCENTRATION_BANDS:
        stop = min(int(round(edge * ordered.size)), ordered.size)
        if stop <= start:
            continue
        share = float(cumulative[stop - 1] - (cumulative[start - 1] if start else 0.0))
        rows.append(
            {
                "label": label,
                "value": share / total,
                "detail": f"{stop - start:,} cycles",
            }
        )
        start = stop
    return rows


def runs_remaining(damage: float) -> float:
    """Further repeats of this recording the structure can still absorb.

    The damage already counted is spent, so this is ``(1 - D) / D`` and not
    ``1 / D`` — the latter counts the run that has just been measured.
    """
    if damage <= 0:
        return math.inf
    return max(0.0, (FAILURE_DAMAGE - damage) / damage)


def format_runs(runs: float) -> str:
    return RUNS_UNLIMITED if math.isinf(runs) else f"{runs:,.1f}" if runs < 100 else f"{runs:,.0f}"


def severity(damage: float) -> str:
    """How urgent this reading is, derived from Miner's rule and nothing else.

    Failure at D >= 1 is the only threshold the Info Kit defines (1.3.1). The middle
    step is that same threshold read forward: with under one run of margin left, the
    next recording of this duty is the one that reaches it.
    """
    if damage >= FAILURE_DAMAGE:
        return SEVERITY_DANGER
    if runs_remaining(damage) < RUNS_REMAINING_ALERT:
        return SEVERITY_CAUTION
    return SEVERITY_CLEAR


def explain(inputs: list[Path], model: DamageModel | None = None) -> list[dict]:
    """Panels explaining a prediction over the same files ``predict`` was given.

    Only the most damaged file is examined in detail. Drawing a concentration
    chart and a trace for all sixteen held-out files would bury the one that
    needs attention, which is the opposite of what a maintenance reader wants.
    """
    if not inputs:
        raise ValueError("No SHM input files to explain.")

    model = load_model() if model is None else model

    bullet_rows: list[dict] = []
    worst: tuple[str, np.ndarray, np.ndarray, float] | None = None
    for path in inputs:
        series = read_stress_series(path)
        cycles = extract_cycles(series)
        damage = model.predict(cycles)
        bullet_rows.append(
            {"label": path.name, "value": damage, "detail": f"{damage:.1%} consumed"}
        )
        if worst is None or damage > worst[3]:
            worst = (path.name, series, cycles, damage)

    name, series, cycles, damage = worst
    per_cycle = cycle_damage(cycles, model.exponent)
    next_steps = RECOMMENDATIONS[severity(damage)]

    return [
        {
            "kind": "verdict",
            "subject": name,
            "headline": VERDICT_HEADLINE.format(damage=damage),
            "severity": severity(damage),
            "recommendation": {
                "title": next_steps["title"].format(file=name),
                "steps": (*next_steps["steps"], RECOMMENDATION_SCOPE),
            },
            "detail": VERDICT_DETAIL.format(
                runs=format_runs(runs_remaining(damage)), count=len(bullet_rows)
            ),
        },
        {
            "kind": "bullet",
            "title": BULLET_TITLE,
            "caption": BULLET_CAPTION,
            "target": FAILURE_DAMAGE,
            "target_label": TARGET_LABEL,
            "rows": bullet_rows,
        },
        {
            "kind": "metrics",
            "title": METRICS_TITLE,
            "caption": METRICS_CAPTION,
            "subject": name,
            "items": [
                {
                    "label": "Fatigue life consumed",
                    "value": f"{damage:.1%}",
                    "detail": f"D = {damage:.4f}",
                },
                {
                    "label": "Recordings left",
                    "value": format_runs(runs_remaining(damage)),
                    "detail": "more runs like this one before D = 1.00",
                },
                {
                    "label": "Stress cycles counted",
                    "value": f"{len(cycles):,}",
                    "detail": f"rainflow-counted from {series.size:,} samples",
                },
            ],
        },
        {
            "kind": "bars",
            "title": BANDS_TITLE,
            "caption": BANDS_CAPTION,
            "subject": name,
            "value_title": BANDS_VALUE_TITLE,
            "rows": _concentration(per_cycle),
        },
        {
            "kind": "line",
            "title": TRACE_TITLE,
            "caption": TRACE_CAPTION,
            "subject": name,
            "x_title": TRACE_X_TITLE,
            "y_title": TRACE_Y_TITLE,
            "points": _envelope(series, TRACE_TARGET_POINTS),
        },
    ]
