"""Cut the continuous controller stream into door cycles.

The stream is only sampled while a door is moving, so a cycle boundary is a silence
rather than a flag transition. Splitting on silence reproduces all 110 labelled
segments exactly, which is what makes every IoU in the official metric equal to 1.0.
"""

import pandas as pd

from . import config

_TIME_FIELDS = ("year", "month", "day", "hour", "minute", "second")


def parse_datetime(series: pd.Series) -> pd.Series:
    """Parse the native Year-Month-Day-Hour-Minute-Second-Millisecond format.

    Used only for measuring gaps. Submission timestamps are never produced from
    this - they are the source strings, echoed.
    """
    parts = series.str.split("-", expand=True).astype(int)
    stamps = pd.to_datetime(dict(zip(_TIME_FIELDS, (parts[i] for i in range(6)))))
    return stamps + pd.to_timedelta(parts[6], unit="ms")


def assign_segments(frame: pd.DataFrame) -> pd.Series:
    """Number each row with the cycle it belongs to."""
    stamps = parse_datetime(frame[config.COLUMN_TIME])
    gaps = stamps.diff().dt.total_seconds().fillna(0.0)
    return (gaps > config.CYCLE_GAP_SECONDS).cumsum()


def infer_operation(rows: pd.DataFrame) -> str:
    """Open or Close, from whichever movement flag is asserted during the cycle."""
    if rows[config.COLUMN_OPENING].mean() > rows[config.COLUMN_CLOSING].mean():
        return config.OPERATION_OPEN
    return config.OPERATION_CLOSE


def segment_bounds(frame: pd.DataFrame) -> pd.DataFrame:
    """One row per cycle: its raw boundary strings, its operation and its length."""
    if config.COLUMN_TIME not in frame.columns:
        raise KeyError(f"Stream is missing the {config.COLUMN_TIME!r} column.")

    records = []
    for segment_id, rows in frame.groupby(assign_segments(frame), sort=True):
        times = rows[config.COLUMN_TIME]
        records.append(
            {
                "segment_id": int(segment_id),
                # Echoed verbatim: the native format is not zero padded, so any
                # round trip through a formatter would stop every segment matching.
                "start_time": times.iloc[0],
                "end_time": times.iloc[-1],
                "operation": infer_operation(rows),
                "n_rows": len(rows),
            }
        )
    return pd.DataFrame.from_records(records)
