"""Read the Door streams and the answer file. No feature logic lives here."""

from pathlib import Path

import pandas as pd

from ..common import config as common_config
from ..common.io import read_table
from . import config, segment

_SUBSYSTEM = "door"


def train_stream_path() -> Path:
    return common_config.TRAIN_PATHS[_SUBSYSTEM]


def test_stream_path() -> Path:
    return common_config.TEST_PATHS[_SUBSYSTEM]


def load_stream(path: str | Path) -> pd.DataFrame:
    """Read one continuous controller recording."""
    frame = read_table(path)
    if frame.empty:
        raise ValueError(f"Door stream is empty: {path}")
    return frame


def load_labels() -> pd.DataFrame:
    """Read Train_Segments_Answer.csv, the ground truth for Train.csv."""
    return read_table(common_config.LABEL_PATHS[_SUBSYSTEM])


def labelled_segments() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """The training stream, its segment bounds, and the status aligned to them.

    Alignment is positional: the answer file is ordered by segment, and the gap
    split reproduces that order exactly (asserted in tests/door/test_segment.py).
    """
    stream = load_stream(train_stream_path())
    bounds = segment.segment_bounds(stream)
    answer = load_labels()
    if len(bounds) != len(answer):
        raise ValueError(
            f"Segmented {len(bounds)} cycles but the answer file has {len(answer)} rows."
        )
    return stream, bounds, answer[config.ANSWER_COLUMN_STATUS].reset_index(drop=True)
