"""Turn a continuous Door stream into submission rows."""

from pathlib import Path

import joblib
import pandas as pd

from . import config, dataset, features, model, segment, train


def _single_input(inputs: list[Path]) -> Path:
    if not inputs:
        raise ValueError("No Door input file was given.")
    if len(inputs) != 1:
        raise ValueError(
            f"Door is one continuous stream; got {len(inputs)} files: {inputs}"
        )
    return inputs[0]


def classify_segments(bounds: pd.DataFrame, stream: pd.DataFrame) -> pd.Series:
    """Label each cycle with the fitted classifier.

    The checkpoint must exist: a missing model is a setup error, not a reason to
    silently emit the majority class into a submission.
    """
    path = train.checkpoint_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"No Door checkpoint at {path}. Run: python -m src.door.train"
        )
    estimator = joblib.load(path)
    table = features.build(stream)
    if len(table) != len(bounds):
        raise ValueError(
            f"Feature rows ({len(table)}) and segment bounds ({len(bounds)}) disagree."
        )
    flags = estimator.predict(table[list(model.FEATURE_COLUMNS)].values)
    labels = [
        config.LABEL_ABNORMAL if flag else config.LABEL_NORMAL for flag in flags
    ]
    return pd.Series(labels, index=bounds.index)


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
