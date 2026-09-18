"""The Door estimator and its hyperparameters. No IO.

One feature does the work, so this is effectively a decision stump that derives its
own split. It is preferred over a hardcoded comparison because it reports a
probability for the app and gives the write-up a real fitted model to compare
against the threshold baseline.
"""

from sklearn.ensemble import HistGradientBoostingClassifier

from ..common.config import RANDOM_SEED

FEATURE_COLUMNS = ("ratio",)

MAX_ITER = 200


def build_estimator() -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        max_iter=MAX_ITER, random_state=RANDOM_SEED
    )
