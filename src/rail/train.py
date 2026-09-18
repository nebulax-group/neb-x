"""Extract, cross-validate and fit the rail classifier. Writes under outputs/.

The feature cache holds every training file. Dropping the two byte-identical
duplicates is a fitting decision, so it happens here rather than at extraction.

Scoring is macro F1 and only macro F1 -- accuracy reads 0.86 for a model that
never predicts a fault. Fold scores are kept individually rather than averaged
away: at this sample size a candidate has to be differenced against the same
folds, not against a mean from another run (.claude/memory/rail-plan.md).
"""

import pickle
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.model_selection import RepeatedStratifiedKFold

from src.common.config import MODEL_DIRS, RANDOM_SEED, TRAIN_PATHS
from src.common.io import list_data_files
from src.rail import config, dataset, features, model
from src.rail.speed import estimate_speed

FEATURE_CACHE_PATH = MODEL_DIRS[config.SUBSYSTEM_KEY] / config.FEATURE_CACHE_NAME
CHECKPOINT_PATH = MODEL_DIRS[config.SUBSYSTEM_KEY] / config.CHECKPOINT_NAME

FILENAME, LABEL = config.LABEL_COLUMNS


@dataclass(frozen=True)
class TrainingSet:
    """What the model is fitted on: duplicates dropped, labels joined."""

    files: list[str]
    matrix: np.ndarray  # (n_files, len(FEATURE_NAMES))
    labels: np.ndarray  # (n_files,) from config.LABELS
    speeds: np.ndarray  # (n_files,) m/s, for the fast-files-only figure


@dataclass(frozen=True)
class CrossValidation:
    """One repeated-CV run, kept per fold and per repeat rather than summarised."""

    fold_scores: np.ndarray  # (CV_REPEATS * CV_SPLITS,) macro F1
    class_f1: np.ndarray  # (CV_REPEATS, len(LABELS)) from each repeat's own OOF set
    confusion: np.ndarray  # (len(LABELS), len(LABELS)) counts, summed over repeats
    n_samples: int

    @property
    def macro_f1(self) -> float:
        return float(self.fold_scores.mean())

    @property
    def spread(self) -> float:
        return float(self.fold_scores.std())

    @property
    def pooled_macro_f1(self) -> float:
        """Macro F1 over a whole out-of-fold set, which is the graded quantity.

        Not the same number as the per-fold mean, and here 0.011 above it: macro
        F1 is not linear in the confusion matrix, so a fold holding 3 Side I
        files reports that class as confidently as it reports its 47 Normal ones,
        and contributes a zero when it misses all 3. The per-fold mean stays the
        headline only because every figure on record is differenced against fold
        scores; this is the one to expect on the held-out set.
        """
        return float(self.class_f1.mean())


def extract_features(directory: str | Path) -> tuple[np.ndarray, list[str], np.ndarray]:
    """Featurise every file in a folder, one recording at a time.

    Streamed rather than loaded up front: 272 recordings held together would be
    ~2.7 GB, against 744 KB of features. Speed comes back alongside because
    recovering it later means re-reading every CSV for one number per file.
    """
    matrix: list[np.ndarray] = []
    names: list[str] = []
    speeds: list[float] = []
    for path in list_data_files(directory):
        recording = dataset.load_recording(path)
        names.append(recording.source_name)
        matrix.append(features.extract(recording))
        speeds.append(estimate_speed(recording.speed_channel))
    return np.vstack(matrix), names, np.asarray(speeds)


def _staleness(cached: np.lib.npyio.NpzFile) -> str:
    """Why this cache cannot be fitted on, or "" if it can.

    The column names alone do not settle it: config.FEATURE_FINGERPRINT holds the
    settings that change a feature's value without changing its name.
    """
    if "speeds" not in cached or "fingerprint" not in cached:
        return "predates the speed and settings vectors"
    if tuple(cached["columns"]) != features.FEATURE_NAMES:
        return "was built from a different feature set"
    if str(cached["fingerprint"]) != config.FEATURE_FINGERPRINT:
        return "was built under different feature settings"
    return ""


def training_features(refresh: bool = False) -> tuple[np.ndarray, list[str], np.ndarray]:
    """The cached training matrix, its filenames and speeds, extracting if missing."""
    if refresh or not FEATURE_CACHE_PATH.exists():
        matrix, names, speeds = extract_features(TRAIN_PATHS[config.SUBSYSTEM_KEY])
        FEATURE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            FEATURE_CACHE_PATH,
            matrix=matrix,
            files=np.array(names),
            speeds=speeds,
            columns=np.array(features.FEATURE_NAMES),
            fingerprint=np.array(config.FEATURE_FINGERPRINT),
        )
        return matrix, names, speeds

    cached = np.load(FEATURE_CACHE_PATH, allow_pickle=False)
    stale = _staleness(cached)
    if stale:
        raise ValueError(
            f"{FEATURE_CACHE_PATH.name} {stale}. Re-extract with refresh=True."
        )
    return cached["matrix"], list(cached["files"]), cached["speeds"]


def training_set(refresh: bool = False) -> TrainingSet:
    """Join the cache to Train_Labels.csv and drop the duplicate recordings.

    The duplicates leave the cache intact and go here instead: a pre-filtered
    artefact would be silently wrong for anything that is not this one fit.
    """
    matrix, names, speeds = training_features(refresh)
    labels = dataset.load_labels().set_index(FILENAME)[LABEL]

    # Checked both ways. A labelled file missing from the cache is the quieter of
    # the two failures: it trains and scores on a smaller set than the report says.
    unlabelled = sorted(set(names) - set(labels.index))
    if unlabelled:
        raise ValueError(f"Cached files carry no label: {unlabelled}.")
    uncached = sorted(set(labels.index) - set(names))
    if uncached:
        raise ValueError(
            f"{FEATURE_CACHE_PATH.name} is missing labelled files: {uncached}. "
            "Re-extract with refresh=True."
        )

    keep = np.fromiter(
        (name not in config.DUPLICATE_FILES for name in names), dtype=bool, count=len(names)
    )
    kept = [name for name, wanted in zip(names, keep) if wanted]
    return TrainingSet(
        files=kept,
        matrix=matrix[keep],
        labels=labels.loc[kept].to_numpy(),
        speeds=speeds[keep],
    )


def cross_validate(
    matrix: np.ndarray, labels: np.ndarray, seed: int = RANDOM_SEED
) -> CrossValidation:
    """Repeated stratified CV at CV_REPEATS x CV_SPLITS, scored on macro F1.

    Per-class figures come from each repeat's own complete out-of-fold set, not
    from a single pass: with 14 Side I files one file changing fold moves that
    class's recall by 1/14, so a single pass reports mostly fold assignment.
    """
    splitter = RepeatedStratifiedKFold(
        n_splits=config.CV_SPLITS, n_repeats=config.CV_REPEATS, random_state=seed
    )

    fold_scores: list[float] = []
    class_f1: list[np.ndarray] = []
    confusion = np.zeros((len(config.LABELS), len(config.LABELS)), dtype=int)
    out_of_fold = np.empty_like(labels)

    for fold, (fit_index, score_index) in enumerate(splitter.split(matrix, labels), start=1):
        estimator = model.build_classifier()
        estimator.fit(matrix[fit_index], labels[fit_index])
        predicted = estimator.predict(matrix[score_index])
        out_of_fold[score_index] = predicted
        fold_scores.append(
            f1_score(
                labels[score_index],
                predicted,
                labels=config.LABELS,
                average="macro",
                zero_division=0,
            )
        )
        if fold % config.CV_SPLITS == 0:  # a repeat closed, so every file has a prediction
            class_f1.append(
                f1_score(labels, out_of_fold, labels=config.LABELS, average=None, zero_division=0)
            )
            confusion += confusion_matrix(labels, out_of_fold, labels=config.LABELS)

    return CrossValidation(
        fold_scores=np.asarray(fold_scores),
        class_f1=np.vstack(class_f1),
        confusion=confusion,
        n_samples=len(labels),
    )


def fit_checkpoint(training: TrainingSet, validation: CrossValidation) -> dict:
    """Fit on every kept file and package what predict.py has to verify.

    No scaler rides along: the booster is scale-invariant across band energies
    spanning decades and routes the undefined wavelength features as NaN, which
    is why it is the shipped estimator rather than the linear baseline.
    """
    estimator = model.build_classifier()
    estimator.fit(training.matrix, training.labels)
    return {
        "estimator": estimator,
        "columns": features.FEATURE_NAMES,
        # The same guard the cache carries, and needed more here: this is the one
        # artefact on the path to the graded CSV, and the column names alone do
        # not notice a retuned Welch window or a swapped pair of rails.
        "fingerprint": config.FEATURE_FINGERPRINT,
        "labels": config.LABELS,
        "n_training_files": len(training.files),
        "excluded_files": config.DUPLICATE_FILES,
        "cv_macro_f1": validation.macro_f1,
        "cv_spread": validation.spread,
        "cv_pooled_macro_f1": validation.pooled_macro_f1,
        "seed": RANDOM_SEED,
    }


def save_checkpoint(checkpoint: dict) -> None:
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CHECKPOINT_PATH.open("wb") as handle:
        pickle.dump(checkpoint, handle)


def _format_report(title: str, validation: CrossValidation) -> str:
    """One CV run as the block that goes in the write-up, per-class and all."""
    per_class = "  ".join(
        f"{label} {score:.3f}"
        for label, score in zip(config.LABELS, validation.class_f1.mean(axis=0))
    )
    rows = "\n".join(
        f"    {label:<8}" + "".join(f"{count / config.CV_REPEATS:8.1f}" for count in row)
        for label, row in zip(config.LABELS, validation.confusion)
    )
    return (
        f"{title} (n={validation.n_samples})\n"
        f"  macro F1   {validation.macro_f1:.3f} +/- {validation.spread:.3f}"
        f"  over {len(validation.fold_scores)} folds\n"
        f"  pooled     {validation.pooled_macro_f1:.3f}"
        f"  macro F1 of a whole out-of-fold set, as the organisers score it\n"
        f"  per class  {per_class}\n"
        f"  confusion, mean per repeat (rows true, cols predicted)\n{rows}"
    )


def main(refresh: bool = False) -> None:
    started = time.perf_counter()
    training = training_set(refresh)
    print(
        f"{len(training.files)} files x {training.matrix.shape[1]} features "
        f"({', '.join(config.DUPLICATE_FILES)} dropped as duplicates)"
    )

    validation = cross_validate(training.matrix, training.labels)
    print(_format_report(f"{config.CV_REPEATS}x{config.CV_SPLITS} repeated stratified CV", validation))

    # Banked before the diagnostic below, not after. That one runs a second CV on
    # a subset small enough to fail its own stratification, and it must not be
    # able to throw away a fit that has already succeeded.
    save_checkpoint(fit_checkpoint(training, validation))
    print(f"checkpoint -> {CHECKPOINT_PATH} in {time.perf_counter() - started:.0f}s")

    # The headline can be had partly for free from "slow implies Normal"; this
    # subset removes that shortcut by construction, so it is the honest figure.
    # Its folds are its own -- a subset cannot be scored on the full set's
    # partitions -- so read it against the headline, never differenced from it.
    fast = training.speeds >= config.FAST_SPEED_MS
    print(
        _format_report(
            f"the same again over files at or above {config.FAST_SPEED_MS} m/s",
            cross_validate(training.matrix[fast], training.labels[fast]),
        )
    )


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv[1:])
