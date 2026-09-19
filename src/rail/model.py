"""The rail estimators and their hyperparameters. No fitting, no IO.

Flat 3-class, not per-side binary: that framing was built, tested and refuted
(.claude/memory/rail-plan.md). lightgbm is excluded project-wide, so the booster
is sklearn's.
"""

from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.common.config import RANDOM_SEED
from src.rail import config


def build_classifier() -> HistGradientBoostingClassifier:
    """The estimator rail ships. 14 Side I files against 234 Normal need the weight."""
    return HistGradientBoostingClassifier(
        class_weight=config.MODEL_CLASS_WEIGHT,
        max_iter=config.MODEL_MAX_ITER,
        random_state=RANDOM_SEED,
    )


def build_linear_baseline() -> Pipeline:
    """A regularised linear comparison for the write-up's model-selection line.

    Both steps are here because the booster does not need either: it takes NaN
    natively, where the wavelength features are undefined on stationary files,
    and it is scale-invariant across band energies spanning several decades.
    """
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            (
                "logistic",
                LogisticRegression(
                    C=config.LINEAR_C,
                    class_weight=config.MODEL_CLASS_WEIGHT,
                    max_iter=config.LINEAR_MAX_ITER,
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )
