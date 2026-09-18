"""Check a prediction frame against the shipped example for its subsystem.

The example CSVs in reference/submission_format/ are the schema contract. Column
names and their order are taken from there rather than restated here, so a change
in the shipped examples cannot silently disagree with us.
"""

import pandas as pd

from ..common import config
from ..common.io import read_table


def expected_columns(subsystem: str) -> list[str]:
    if subsystem not in config.SUBSYSTEMS:
        raise ValueError(f"Unknown subsystem: {subsystem!r}")
    return list(read_table(config.EXAMPLE_PREDICTION_PATHS[subsystem]).columns)


def validate(subsystem: str, frame: pd.DataFrame) -> None:
    """Raise ValueError unless the frame matches the shipped example's schema."""
    expected = expected_columns(subsystem)
    if list(frame.columns) != expected:
        raise ValueError(
            f"{subsystem} prediction columns {list(frame.columns)} "
            f"do not match the required columns {expected}."
        )
    if frame.empty:
        raise ValueError(f"{subsystem} prediction frame is empty.")
    if frame.isna().any().any():
        raise ValueError(f"{subsystem} prediction frame contains missing values.")
