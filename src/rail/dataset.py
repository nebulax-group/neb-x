"""Rail CSVs -> arrays, and Train_Labels.csv -> a DataFrame. No feature logic.

Column positions come from config.py. The header check on every load is what
keeps that derivation honest: mis-split channels would swap the two rails.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.common.config import LABEL_PATHS
from src.common.io import read_table
from src.rail import config

FILENAME, LABEL = config.LABEL_COLUMNS

_VIBRATION_INDEX = np.fromiter(config.VIBRATION_COLUMNS, dtype=int)
_SHOCK_INDEX = np.fromiter(config.SHOCK_COLUMNS, dtype=int)


@dataclass(frozen=True)
class Recording:
    """One second of an 8-car train crossing a section of track.

    Both matrices are in axle-box order, which config.SIDE_BOXES indexes into.
    Vibration and shock stay separate: different scales, never pooled.
    """

    source_name: str
    speed_channel: np.ndarray  # (SAMPLES_PER_FILE,) tachometer square wave, 0/1
    vibration: np.ndarray  # (SAMPLES_PER_FILE, N_AXLE_BOXES) m/s^2
    shock: np.ndarray  # (SAMPLES_PER_FILE, N_AXLE_BOXES) m/s^2


def _describe_header_mismatch(columns: tuple[str, ...]) -> str:
    """Name the first difference from the expected schema, or "" if there is none."""
    if len(columns) != config.N_COLUMNS:
        return f"expected {config.N_COLUMNS} columns, found {len(columns)}"
    for index, (found, expected) in enumerate(zip(columns, config.EXPECTED_HEADERS)):
        if found != expected:
            return f"column {index} is {found!r}, expected {expected!r}"
    return ""


def load_recording(path: str | Path) -> Recording:
    """Read one rail CSV into its speed, vibration and shock channels."""
    path = Path(path)
    frame = read_table(path)

    mismatch = _describe_header_mismatch(tuple(frame.columns))
    if mismatch:
        raise ValueError(f"{path.name} does not match the rail schema: {mismatch}.")
    if len(frame) != config.SAMPLES_PER_FILE:
        raise ValueError(
            f"{path.name} holds {len(frame)} samples, expected {config.SAMPLES_PER_FILE}."
        )

    values = frame.to_numpy(dtype=float)
    # A NaN would reach every band of that box through Welch without a trace.
    if not np.isfinite(values).all():
        raise ValueError(f"{path.name} contains missing or non-finite samples.")

    return Recording(
        source_name=path.name,
        speed_channel=values[:, config.SPEED_COLUMN],
        vibration=values[:, _VIBRATION_INDEX],
        shock=values[:, _SHOCK_INDEX],
    )


def load_labels() -> pd.DataFrame:
    """Read Train_Labels.csv as filename, label -- one row per training file."""
    path = LABEL_PATHS[config.SUBSYSTEM_KEY]
    frame = read_table(path)

    if tuple(frame.columns) != config.LABEL_COLUMNS:
        raise ValueError(
            f"{path.name} has columns {tuple(frame.columns)}, "
            f"expected {config.LABEL_COLUMNS}."
        )
    unknown = sorted(set(frame[LABEL]) - set(config.LABELS))
    if unknown:
        raise ValueError(f"{path.name} uses labels outside the vocabulary: {unknown}.")
    duplicated = frame[FILENAME][frame[FILENAME].duplicated()].tolist()
    if duplicated:
        raise ValueError(f"{path.name} labels these files more than once: {duplicated}.")

    return frame
