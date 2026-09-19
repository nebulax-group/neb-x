"""Read ACV case workbooks without assuming a fixed column list. No feature logic."""

from pathlib import Path

import pandas as pd

from ..common import config as common_config
from ..common.io import list_data_files, read_table
from . import config

_SUBSYSTEM = "acv"


def load_labels() -> pd.DataFrame:
    """Read Train_Labels.csv keeping car ids as strings.

    Without dtype=str, '01' becomes the integer 1 and the submission would say
    '1|3|7' instead of '01|03|07', which scores zero.
    """
    return read_table(
        common_config.LABEL_PATHS[_SUBSYSTEM],
        dtype={config.LABEL_CAR_COLUMN: str, config.LABEL_FILENAME_COLUMN: str},
    )


def car_columns(frame: pd.DataFrame) -> dict[str, dict[str, str]]:
    """Map car id -> parameter name -> the column holding it."""
    cars: dict[str, dict[str, str]] = {}
    for column in frame.columns:
        match = config.CAR_COLUMN_PATTERN.match(str(column))
        if match:
            cars.setdefault(match.group(1), {})[match.group(2)] = str(column)
    if not cars:
        raise ValueError("No per-car columns found; the file layout is unexpected.")
    return cars


def resolve(params: dict[str, str], candidates: tuple[str, ...]) -> str:
    """Return the column for the first candidate parameter this file actually has."""
    for candidate in candidates:
        if candidate in params:
            return params[candidate]
    raise KeyError(
        f"This file has none of {list(candidates)}; available: {sorted(params)[:8]}"
    )


def load_case(path: str | Path) -> tuple[pd.DataFrame, dict[str, dict[str, str]]]:
    frame = read_table(path)
    return frame, car_columns(frame)


def train_case_paths() -> list[Path]:
    return list_data_files(common_config.TRAIN_PATHS[_SUBSYSTEM])


def validation_case_paths() -> list[Path]:
    """Training cases that share the test file's schema."""
    return [p for p in train_case_paths() if p.name not in config.EXCLUDED_FROM_VALIDATION]


def test_case_paths() -> list[Path]:
    return list_data_files(common_config.TEST_PATHS[_SUBSYSTEM])
