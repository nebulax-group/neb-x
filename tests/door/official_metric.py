"""Reference implementation of docs/door/info_kit.md section 4.1-4.2.

Transcribed from the info kit so the design's central claim - that with exact
segmentation the IoU-weighted F1 collapses to plain accuracy - is demonstrated
rather than argued. Test-only; the shipped metric is src/common/metrics.py.
"""

import pandas as pd

from src.door.segment import parse_datetime

_EPOCH = pd.Timestamp("1970-01-01")


def _to_epoch_seconds(stamps: pd.Series) -> pd.Series:
    """Seconds since epoch, as floats.

    Not `.astype("int64") / 1e9`: pandas 3 stores these datetime64 values at
    microsecond resolution by default, so `.astype("int64")` counts
    microseconds, not nanoseconds, and dividing by 1e9 silently returns values
    1000x too small (no warning raised). Subtracting the epoch and taking
    `.dt.total_seconds()` is resolution-agnostic and gives real seconds.
    """
    return (stamps - _EPOCH).dt.total_seconds()


def _spans(frame: pd.DataFrame) -> list[tuple[float, float, str]]:
    starts = _to_epoch_seconds(parse_datetime(frame["start_time"]))
    ends = _to_epoch_seconds(parse_datetime(frame["end_time"]))
    return list(zip(starts, ends, frame["prediction"]))


def _iou(a: tuple[float, float, str], b: tuple[float, float, str]) -> float:
    intersection = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    union = (a[1] - a[0]) + (b[1] - b[0]) - intersection
    return intersection / union if union > 0 else 0.0


def iou_weighted_f1(truth: pd.DataFrame, predicted: pd.DataFrame) -> float:
    true_spans, pred_spans = _spans(truth), _spans(predicted)

    # Same label required; overlap required; then greedy by highest IoU, one to one.
    candidates = [
        (_iou(t, p), ti, pi)
        for ti, t in enumerate(true_spans)
        for pi, p in enumerate(pred_spans)
        if t[2] == p[2]
    ]
    candidates = sorted((c for c in candidates if c[0] > 0), key=lambda c: -c[0])

    used_true, used_pred, total_iou = set(), set(), 0.0
    for iou, ti, pi in candidates:
        if ti in used_true or pi in used_pred:
            continue
        used_true.add(ti)
        used_pred.add(pi)
        total_iou += iou

    # An empty truth or predicted frame is not handled here: parse_datetime already
    # raises before this function reaches it, on an empty frame's string columns.
    soft_recall = total_iou / len(true_spans)
    soft_precision = total_iou / len(pred_spans)
    if soft_recall + soft_precision == 0:
        return 0.0
    return 2 * soft_recall * soft_precision / (soft_recall + soft_precision)
