"""Cycles to a feature matrix. No IO, no model.

One feature carries the decision: the cycle's mean motor current divided by the
median mean-current of the same operation *within the same recording*. Absolute
milliamps do not transfer between doors - the info kit says so in 1.2.2 and the
data agrees - but a cycle's excess over its own door's typical cycle does.
"""

import pandas as pd

from . import config, segment


def build(stream: pd.DataFrame) -> pd.DataFrame:
    """One row per cycle: its operation, its mean current, and its normalised ratio."""
    missing = {config.COLUMN_CURRENT, config.COLUMN_OPENING, config.COLUMN_CLOSING}
    missing -= set(stream.columns)
    if missing:
        raise KeyError(f"Stream is missing required columns: {sorted(missing)}")

    records = []
    for segment_id, rows in stream.groupby(segment.assign_segments(stream), sort=True):
        records.append(
            {
                "segment_id": int(segment_id),
                "operation": segment.infer_operation(rows),
                "mean_current": float(rows[config.COLUMN_CURRENT].mean()),
            }
        )
    table = pd.DataFrame.from_records(records)

    # The baseline is recomputed from whichever recording is being scored, so the
    # same code calibrates itself on a door it has never seen. Never replace this
    # with a scaler fitted on the training stream.
    baseline = table.groupby("operation")["mean_current"].transform("median")
    if (baseline <= 0).any():
        raise ValueError("A per-operation current baseline was not positive.")
    table["ratio"] = table["mean_current"] / baseline
    return table
