"""Check stress uploads before loading the SHM model."""

from pathlib import Path

import numpy as np

from .dataset import read_stress_series


def validate(inputs: list[Path]) -> None:
    for path in inputs:
        values = read_stress_series(path)
        if values.size < 2:
            raise ValueError(f"{path.name}: upload at least two stress samples.")
        if not np.isfinite(values).all():
            raise ValueError(f"{path.name}: stress samples must be finite numbers; check missing or invalid values.")
