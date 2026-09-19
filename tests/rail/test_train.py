"""The cache and the label join, which are where a quiet wrong answer would come from.

Fitting on a stale cache is the failure this package is most exposed to: the
matrix on disk survives every edit to features.py, still has 228 columns, still
joins to every label, and reports a score for a feature set nobody is shipping.
So the three ways the cache can be stale each get a test, and so does the join
that would otherwise train on fewer files than the report claims.

The cross-validation run at the end is the real one at one repeat rather than
ten. It takes a few seconds and is the only test here that fits anything.
"""

import hashlib

import numpy as np
import pytest

from src.common.config import RANDOM_SEED, TRAIN_PATHS
from src.rail import config, features, train


@pytest.fixture(scope="module")
def training():
    """The cached matrix joined to the labels, duplicates already dropped."""
    return train.training_set()


def cache_file(path, **changes):
    """A feature cache with one field spoiled, written where train.py looks."""
    fields = {
        "matrix": np.zeros((1, len(features.FEATURE_NAMES))),
        "files": np.array(["Train1.csv"]),
        "speeds": np.zeros(1),
        "columns": np.array(features.FEATURE_NAMES),
        "fingerprint": np.array(config.FEATURE_FINGERPRINT),
    }
    fields.update(changes)
    np.savez(path, **{name: value for name, value in fields.items() if value is not None})
    return path.with_suffix(".npz")


def test_the_two_documented_duplicates_really_are_byte_identical():
    """Dropped so a fold cannot score against its own example. Both are Normal,
    so neither touches the two classes the macro F1 actually turns on."""
    folder = TRAIN_PATHS[config.SUBSYSTEM_KEY]
    for original, copy in (("Train107.csv", "Train115.csv"), ("Train165.csv", "Train187.csv")):
        assert copy in config.DUPLICATE_FILES
        digests = {
            hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in (original, copy)
        }
        assert len(digests) == 1, f"{original} and {copy} are no longer the same file"


def test_the_fitted_set_is_every_labelled_file_less_the_duplicates(training, labels):
    assert len(training.files) == len(labels) - len(config.DUPLICATE_FILES) == 270
    assert set(training.files).isdisjoint(config.DUPLICATE_FILES)
    assert training.matrix.shape == (270, len(features.FEATURE_NAMES))
    assert training.labels.shape == training.speeds.shape == (270,)
    # The label for each row is that row's own file's label, not the file order's.
    assert list(training.labels) == [labels[name] for name in training.files]


def test_the_class_balance_the_model_is_fitted_at(training):
    counts = {label: int((training.labels == label).sum()) for label in config.LABELS}
    assert counts == {"Normal": 232, "Side I": 14, "Side II": 24}


def test_no_fault_file_was_recorded_below_the_documented_fault_floor(training):
    """The speed confound, over all 270 files rather than a sample.

    Every reported figure for the honest subset rests on this being true, so it
    is measured here instead of remembered: no fault file is slower than
    FAST_SPEED_MS, and a large part of Normal is.
    """
    fault = np.isin(training.labels, config.SIDE_LABELS)
    assert training.speeds[fault].min() >= config.FAST_SPEED_MS
    assert (training.speeds[~fault] < config.FAST_SPEED_MS).sum() > 100
    # The 38 files whose tachometer never transitions are all Normal.
    assert set(training.labels[training.speeds == 0.0]) == {config.LABEL_NORMAL}


def test_a_cache_built_from_a_different_feature_set_is_refused(tmp_path, monkeypatch):
    path = cache_file(tmp_path / "stale", columns=np.array(["something_else"]))
    monkeypatch.setattr(train, "FEATURE_CACHE_PATH", path)
    with pytest.raises(ValueError, match="different feature set"):
        train.training_features()


def test_a_cache_built_under_different_settings_is_refused(tmp_path, monkeypatch):
    """The column names cannot see this one: a retuned Welch window or a flipped
    side parity changes every value and renames nothing."""
    path = cache_file(tmp_path / "retuned", fingerprint=np.array("0|0|0"))
    monkeypatch.setattr(train, "FEATURE_CACHE_PATH", path)
    with pytest.raises(ValueError, match="different feature settings"):
        train.training_features()


def test_a_cache_from_before_the_speed_and_settings_vectors_is_refused(tmp_path, monkeypatch):
    path = cache_file(tmp_path / "old", speeds=None, fingerprint=None)
    monkeypatch.setattr(train, "FEATURE_CACHE_PATH", path)
    with pytest.raises(ValueError, match="predates"):
        train.training_features()


def test_a_cache_missing_a_labelled_file_is_refused_rather_than_quietly_shrinking(
    tmp_path, monkeypatch
):
    """The quieter of the two join failures: it fits and scores on a smaller set
    than the report prints, and every number stays plausible."""
    path = cache_file(tmp_path / "partial")
    monkeypatch.setattr(train, "FEATURE_CACHE_PATH", path)
    with pytest.raises(ValueError, match="is missing labelled files"):
        train.training_set()


def test_a_cached_file_with_no_label_is_refused_too(tmp_path, monkeypatch, labels):
    path = cache_file(
        tmp_path / "extra",
        matrix=np.zeros((len(labels) + 1, len(features.FEATURE_NAMES))),
        files=np.array(list(labels.index) + ["Train999.csv"]),
        speeds=np.zeros(len(labels) + 1),
    )
    monkeypatch.setattr(train, "FEATURE_CACHE_PATH", path)
    with pytest.raises(ValueError, match=r"carry no label: \['Train999.csv'\]"):
        train.training_set()


def test_the_pooled_score_is_the_mean_of_whole_out_of_fold_sets_not_of_folds():
    """The two are different numbers and the write-up quotes both, so which is
    which is arithmetic worth pinning rather than remembering."""
    validation = train.CrossValidation(
        fold_scores=np.array([0.5, 0.7, 0.9]),
        class_f1=np.array([[0.9, 0.3, 0.6], [0.9, 0.5, 0.4]]),
        confusion=np.zeros((3, 3), dtype=int),
        n_samples=270,
    )
    assert validation.macro_f1 == pytest.approx(0.7)
    assert validation.spread == pytest.approx(np.std([0.5, 0.7, 0.9]))
    assert validation.pooled_macro_f1 == pytest.approx(0.6)


def test_cross_validation_scores_every_file_once_per_repeat(training, monkeypatch):
    """One repeat of the real thing. Macro F1 and not accuracy: a model that
    never predicts a fault reads 0.86 accurate and is worth 0.308 here."""
    monkeypatch.setattr(config, "CV_REPEATS", 1)
    validation = train.cross_validate(training.matrix, training.labels, seed=RANDOM_SEED)

    assert validation.fold_scores.shape == (config.CV_SPLITS,)
    assert validation.class_f1.shape == (1, len(config.LABELS))
    assert validation.n_samples == len(training.labels)
    # Each repeat predicts every file exactly once, so the confusion matrix for
    # one repeat holds one entry per file and no more.
    assert validation.confusion.sum() == len(training.labels)
    assert np.array_equal(
        validation.confusion.sum(axis=1),
        [int((training.labels == label).sum()) for label in config.LABELS],
    )
    assert 0.0 <= validation.macro_f1 <= 1.0
    # The majority-class floor at this balance. Below it the pipeline is broken,
    # not merely weak -- predicting Normal everywhere would score better.
    assert validation.pooled_macro_f1 > 0.308


def test_the_report_names_every_class_and_says_which_figure_is_which():
    validation = train.CrossValidation(
        fold_scores=np.array([0.75]),
        class_f1=np.array([[0.92, 0.51, 0.80]]),
        confusion=np.zeros((3, 3), dtype=int),
        n_samples=270,
    )
    report = train._format_report("10x5 repeated stratified CV", validation)
    assert "n=270" in report
    for label in config.LABELS:
        assert label in report
    assert "macro F1" in report and "pooled" in report
