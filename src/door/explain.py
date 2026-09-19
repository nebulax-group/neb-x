"""Turn one run of the Door model into the panels the app draws beside the rows.

``predict`` answers which cycles resisted; this answers where they sit in the run
and what the model actually measured. It classifies by calling ``predict`` rather
than by repeating its logic, so the picture and the submitted CSV cannot disagree.

Panels are plain dicts, not a type of ours, so the app can draw them without
importing this subsystem. The shapes are documented in ``src/app/services.py``.
"""

from pathlib import Path

import pandas as pd

from . import dataset, features, predict, segment
from .config import (
    ABNORMAL_RUN_ALERT,
    COLUMN_CURRENT,
    LABEL_ABNORMAL,
    LABEL_NORMAL,
    OPERATIONS,
    RECOMMENDATIONS,
    SEVERITY_CAUTION,
    SEVERITY_CLEAR,
    SEVERITY_DANGER,
)

VERDICT_FOUND = "{flagged} of {total} cycles show abnormal resistance"
VERDICT_NONE = "No abnormal resistance in {total} cycles"
VERDICT_DETAIL_RUN = "Longest unbroken run: {run} of them back to back."
VERDICT_DETAIL_CLEAR = "Every cycle sits within this door's own normal current."

STRIP_TITLE = "Every cycle in order"
STRIP_CAPTION = "One block per open or close. Click a cycle to keep its details in view."
STRIP_CELL_DETAIL = "Cycle {number} · {operation} · {status}. Start: {start}. End: {end}."
# The ends of the recording, not ends of a train: this is one door's stream in time.
STRIP_HEAD = "First cycle"
STRIP_TAIL = "Latest cycle"

METRICS_TITLE = "What the model measured"
METRICS_CAPTION = (
    "Each cycle is judged against the median cycle of the same move in this same "
    "recording, never against a fixed current."
)

SPLIT_TITLE = "Opening or closing"
SPLIT_CAPTION = "Which move resists. It says where on the door to look first."
SPLIT_VALUE_TITLE = "Cycles flagged"
SPLIT_DETAIL = "{flagged} of {total} cycles"

TRACE_TITLE = "Motor current"
TRACE_CAPTION = "The whole recording. Each hump is one cycle, and a stiff one pulls harder."
TRACE_X_TITLE = "Sample"
TRACE_Y_TITLE = "Motor current (mA)"


def longest_run(flags: pd.Series) -> int:
    """The most consecutive flagged cycles anywhere in the stream."""
    if not flags.any():
        return 0
    blocks = (~flags).cumsum()
    return int(flags.groupby(blocks).sum().max())


def severity(flags: pd.Series) -> str:
    """How urgent this stream is: nothing flagged, some, or a sustained run."""
    if not flags.any():
        return SEVERITY_CLEAR
    if longest_run(flags) >= ABNORMAL_RUN_ALERT:
        return SEVERITY_DANGER
    return SEVERITY_CAUTION


def _cells(rows: pd.DataFrame, bounds: pd.DataFrame) -> list[dict]:
    return [
        {
            "label": f"{number:02d}",
            "state": SEVERITY_DANGER if status == LABEL_ABNORMAL else SEVERITY_CLEAR,
            "detail": STRIP_CELL_DETAIL.format(
                number=number, operation=operation, status=status, start=start, end=end
            ),
        }
        for number, (status, operation, start, end) in enumerate(
            zip(rows["prediction"], bounds["operation"], rows["start_time"], rows["end_time"]), start=1
        )
    ]


def _by_operation(bounds: pd.DataFrame, flags: pd.Series) -> list[dict]:
    """Share of each move's cycles that were flagged.

    Rates rather than a split of the flagged cycles: a reader wants to know whether
    opening resists more often than closing, and the two moves are not equally
    numerous in a recording, so the raw counts alone would answer a different question.
    """
    rows = []
    for operation in OPERATIONS:
        of_this_move = bounds["operation"] == operation
        total = int(of_this_move.sum())
        if not total:
            continue
        flagged = int((flags & of_this_move).sum())
        rows.append(
            {
                "label": operation,
                "value": flagged / total,
                "detail": SPLIT_DETAIL.format(flagged=flagged, total=total),
            }
        )
    return rows


def explain(inputs: list[Path]) -> list[dict]:
    """Panels explaining a prediction over the same file ``predict`` was given."""
    rows = predict.predict(inputs)
    # predict rejects anything but a single stream, so this is safe only after it.
    stream = dataset.load_stream(Path(inputs[0]))
    bounds = segment.segment_bounds(stream)
    table = features.build(stream)

    flags = rows["prediction"] == LABEL_ABNORMAL
    flagged, total = int(flags.sum()), len(rows)
    current = stream[COLUMN_CURRENT]

    panels = [
        {
            "kind": "verdict",
            "subject": Path(inputs[0]).name,
            "headline": (
                VERDICT_FOUND.format(flagged=flagged, total=total)
                if flagged
                else VERDICT_NONE.format(total=total)
            ),
            "severity": severity(flags),
            "recommendation": RECOMMENDATIONS[severity(flags)],
            "detail": (
                VERDICT_DETAIL_RUN.format(run=longest_run(flags))
                if flagged
                else VERDICT_DETAIL_CLEAR
            ),
        },
        {
            "kind": "strip",
            "title": STRIP_TITLE,
            "subject": Path(inputs[0]).name,
            "caption": STRIP_CAPTION,
            "cells": _cells(rows, bounds),
            "head": STRIP_HEAD,
            "tail": STRIP_TAIL,
            "legend": [
                {"state": SEVERITY_CLEAR, "label": LABEL_NORMAL},
                {"state": SEVERITY_DANGER, "label": LABEL_ABNORMAL},
            ],
        },
        {
            "kind": "metrics",
            "title": METRICS_TITLE,
            "caption": METRICS_CAPTION,
            "items": [
                {
                    "label": "Cycles found",
                    "value": f"{total:,}",
                    "detail": f"cut from {len(stream):,} readings at the silences between moves",
                },
                {
                    "label": "Flagged",
                    "value": f"{flagged:,}",
                    "detail": f"{flagged / total:.0%} of the cycles in this recording",
                },
                {
                    "label": "Highest reading",
                    "value": f"{table['ratio'].max():.2f}x",
                    "detail": "the median cycle of the same move on this door",
                },
            ],
        },
    ]

    # Omitted rather than drawn flat when nothing was flagged: every bar would be zero,
    # which says less than the verdict already has and leaves the chart with no scale.
    if flagged:
        panels.append(
            {
                "kind": "bars",
                "title": SPLIT_TITLE,
                "caption": SPLIT_CAPTION,
                "value_title": SPLIT_VALUE_TITLE,
                "rows": _by_operation(bounds, flags),
            }
        )

    panels.append(
        {
            "kind": "line",
            "title": TRACE_TITLE,
            "caption": TRACE_CAPTION,
            "x_title": TRACE_X_TITLE,
            "y_title": TRACE_Y_TITLE,
            "points": (list(range(len(current))), [float(v) for v in current]),
        }
    )
    return panels
