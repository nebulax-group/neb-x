"""Fit the Door classifier, validate it, and write a checkpoint."""

from pathlib import Path

import joblib
import numpy as np
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score

from ..common import config as common_config
from . import config, dataset, features, model

CHECKPOINT_NAME = "classifier.joblib"


def _design_matrix():
    stream, _, status = dataset.labelled_segments()
    table = features.build(stream)
    x = table[list(model.FEATURE_COLUMNS)].values
    y = (status == config.LABEL_ABNORMAL).values
    return x, y


def cross_validate() -> dict:
    """Repeated stratified CV over the 110 labelled cycles, scored as accuracy.

    Accuracy is the right scorer because the official IoU-weighted F1 reduces to it
    when segmentation is exact - demonstrated in tests/door/test_official_metric.py.
    """
    x, y = _design_matrix()
    splitter = RepeatedStratifiedKFold(
        n_splits=config.CV_SPLITS,
        n_repeats=config.CV_REPEATS,
        random_state=config.CV_RANDOM_STATE,
    )
    scores = cross_val_score(
        model.build_estimator(), x, y, cv=splitter, scoring="accuracy"
    )
    return {
        "mean_accuracy": float(np.mean(scores)),
        "std_accuracy": float(np.std(scores)),
        "n_errors": int(round((1 - np.mean(scores)) * len(y))),
        "n_segments": len(y),
    }


def checkpoint_path() -> Path:
    return common_config.MODEL_DIRS["door"] / CHECKPOINT_NAME


def fit_and_save() -> Path:
    x, y = _design_matrix()
    estimator = model.build_estimator()
    estimator.fit(x, y)
    path = checkpoint_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(estimator, path)
    return path


if __name__ == "__main__":
    report = cross_validate()
    print(
        f"Door CV accuracy {report['mean_accuracy']:.4f} "
        f"+/- {report['std_accuracy']:.4f} over {report['n_segments']} cycles "
        f"({report['n_errors']} errors)"
    )
    print("checkpoint ->", fit_and_save())
