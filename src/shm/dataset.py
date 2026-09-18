"""Read SHM dynamic-stress files and their damage labels. IO only, no features."""

from pathlib import Path

import numpy as np
import pandas as pd

from src.common.config import LABEL_PATHS, TEST_PATHS, TRAIN_PATHS
from src.common.io import list_data_files, read_table

from .config import (
    LABEL_COLUMNS,
    STRESS_COLUMN_COUNT,
    STRESS_DTYPE,
    SUBSYSTEM_KEY,
)


def read_stress_series(path: str | Path) -> np.ndarray:
    """One dynamic-stress file -> a 1-D float array.

    The files are headerless, so pandas' default parsing would silently take
    the first sample as a column name. A file with more than one column means a
    header row or a schema change, and is an error rather than a column to pick
    from. Row counts are not enforced: held-out segments may differ in length.
    """
    frame = read_table(path, header=None)
    if frame.shape[1] != STRESS_COLUMN_COUNT:
        raise ValueError(
            f"Expected {STRESS_COLUMN_COUNT} dynamic-stress column in {path}, "
            f"found {frame.shape[1]}."
        )
    return frame.iloc[:, 0].to_numpy(dtype=STRESS_DTYPE)


def read_labels() -> pd.DataFrame:
    """Train_Labels.csv -> one row per training file."""
    path = LABEL_PATHS[SUBSYSTEM_KEY]
    frame = read_table(path)
    missing = [column for column in LABEL_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(
            f"Missing label columns {missing} in {path}. "
            f"Found {list(frame.columns)}."
        )
    return frame


def list_train_files() -> list[Path]:
    """The labelled SHM inputs, in filename order, names untouched."""
    return list_data_files(TRAIN_PATHS[SUBSYSTEM_KEY])


def list_test_files() -> list[Path]:
    """The held-out SHM inputs, in filename order, names untouched."""
    return list_data_files(TEST_PATHS[SUBSYSTEM_KEY])
