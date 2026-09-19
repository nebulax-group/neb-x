"""Check a controller recording before loading the Door classifier."""

from pathlib import Path

import numpy as np
import pandas as pd

from . import config, dataset, segment


def validate(inputs: list[Path]) -> None:
    if len(inputs) != 1:
        raise ValueError(f"Door needs exactly one continuous recording; {len(inputs)} files were added. Remove the extra files.")
    path = inputs[0]
    frame = dataset.load_stream(path)
    required = (config.COLUMN_TIME, config.COLUMN_CURRENT, config.COLUMN_OPENING, config.COLUMN_CLOSING)
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{path.name}: missing Door columns: {', '.join(missing)}.")
    for column in required[1:]:
        values = pd.to_numeric(frame[column], errors="coerce")
        if not np.isfinite(values).all():
            raise ValueError(f"{path.name}: {column} must contain numeric readings without missing values.")
    try:
        stamps = segment.parse_datetime(frame[config.COLUMN_TIME])
    except (ValueError, KeyError, AttributeError, TypeError, OverflowError) as exc:
        raise ValueError(f"{path.name}: Datetime must use the controller's year-month-day-hour-minute-second-millisecond format.") from exc
    if stamps.isna().any() or not stamps.is_monotonic_increasing:
        raise ValueError(f"{path.name}: Datetime must contain valid timestamps in chronological order.")
