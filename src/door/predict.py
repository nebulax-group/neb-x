"""Turn a continuous Door stream into submission rows.

Ships a constant classifier for now so a valid CSV exists before any model does;
Task 8 replaces classify_segments with the fitted model.
"""

from pathlib import Path

import pandas as pd

from . import config, dataset, segment


def _single_input(inputs: list[Path]) -> Path:
    if not inputs:
        raise ValueError("No Door input file was given.")
    if len(inputs) != 1:
        raise ValueError(
            f"Door is one continuous stream; got {len(inputs)} files: {inputs}"
        )
    return inputs[0]


def classify_segments(bounds: pd.DataFrame, stream: pd.DataFrame) -> pd.Series:
    """Constant baseline: the majority class. Replaced in Task 8."""
    return pd.Series([config.LABEL_NORMAL] * len(bounds), index=bounds.index)


def predict(inputs: list[Path]) -> pd.DataFrame:
    """Return exactly the submission rows for this subsystem."""
    stream = dataset.load_stream(_single_input(inputs))
    bounds = segment.segment_bounds(stream)
    result = pd.DataFrame(
        {
            "start_time": bounds["start_time"],
            "end_time": bounds["end_time"],
            "prediction": classify_segments(bounds, stream),
        }
    )
    return result.reset_index(drop=True)
