"""Fit the SHM S-N curve on the labelled files and write the checkpoint.

Run as ``python -m src.shm.train``. Reads ``data/shm/train`` through
``dataset``, reduces each history with ``features``, fits the two parameters
with ``model``, and is one of only two files here allowed to write to
``outputs/``.

The exponent is found in two passes, coarse then fine, because ``S(m)`` is
expensive per exponent and the optimum is sharp: a single grid fine enough to
resolve it would spend almost all its work far from the answer.

Validation is leave-one-out rather than a held-out fold. The model has two
parameters against 64 files, so a single fold would be noisier than the
generalisation gap it is meant to measure, and refitting is free once the
damage-sum matrix is cached. LOO is only honest here *because* the model is
this small — with a high-capacity model it would leak.
"""

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from .config import (
    CHECKPOINT_PATH,
    EXPECTED_TRAIN_FILES,
    EXPONENT_COARSE_STEP,
    EXPONENT_FINE_STEP,
    EXPONENT_MAX,
    EXPONENT_MIN,
    LABEL_DAMAGE_COLUMN,
    LABEL_FILENAME_COLUMN,
)
from .dataset import list_train_files, read_labels, read_stress_series
from .features import extract_cycles
from .model import (
    DamageModel,
    coarse_grid,
    damage_sums,
    fine_grid,
    fit,
    mape,
)

WORST_FILES_REPORTED = 5


def load_labelled_files() -> tuple[list[Path], np.ndarray]:
    """Training paths and their damages, aligned by filename.

    Matching on the filename rather than on row order: the label file and a
    sorted directory listing agree today, but a silent misalignment here would
    fit the curve to the wrong labels and still look like a clean result.
    """
    labels = read_labels()
    damage_by_name = dict(
        zip(labels[LABEL_FILENAME_COLUMN], labels[LABEL_DAMAGE_COLUMN], strict=True)
    )
    paths = list_train_files()

    unlabelled = [path.name for path in paths if path.name not in damage_by_name]
    if unlabelled:
        raise ValueError(f"No damage label for {unlabelled}.")

    damages = np.array([damage_by_name[path.name] for path in paths], dtype=float)
    return paths, damages


def extract_all(paths: list[Path]) -> list[np.ndarray]:
    """Every training history reduced to its rainflow cycles."""
    return [extract_cycles(read_stress_series(path)) for path in paths]


def _column_for(exponents: np.ndarray, exponent: float) -> int:
    matches = np.flatnonzero(exponents == exponent)
    if matches.size != 1:
        raise ValueError(f"Exponent {exponent} is not a unique column of the grid.")
    return int(matches[0])


def predict_from_sums(
    model: DamageModel, sums: np.ndarray, exponents: np.ndarray
) -> np.ndarray:
    """Damages implied by a cached matrix, without touching the cycles again."""
    return sums[:, _column_for(exponents, model.exponent)] / model.coefficient


def cross_validate(
    sums: np.ndarray, exponents: np.ndarray, damages: np.ndarray
) -> np.ndarray:
    """Absolute percentage error on each file when it is held out of the fit."""
    errors = np.empty(damages.size, dtype=float)
    for index in range(damages.size):
        kept = np.arange(damages.size) != index
        fold = fit(sums[kept], exponents, damages[kept])
        predicted = sums[index, _column_for(exponents, fold.exponent)] / fold.coefficient
        errors[index] = abs(1.0 - predicted / damages[index])
    return errors


def build_report(
    damages: np.ndarray,
    fit_mape: float,
    cv_errors: np.ndarray,
    names: list[str],
) -> dict:
    worst = np.argsort(cv_errors)[::-1][:WORST_FILES_REPORTED]
    return {
        "trained_on": int(damages.size),
        "fit_mape": float(fit_mape),
        "cv_mape": float(cv_errors.mean()),
        "cv_score": float(max(0.0, 1.0 - cv_errors.mean())),
        "cv_folds": int(damages.size),
        "exponent_grid": {
            "min": EXPONENT_MIN,
            "max": EXPONENT_MAX,
            "coarse_step": EXPONENT_COARSE_STEP,
            "fine_step": EXPONENT_FINE_STEP,
        },
        "worst_files": {names[index]: float(cv_errors[index]) for index in worst},
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def write_checkpoint(model: DamageModel, report: dict, path: Path | None = None) -> Path:
    """Write the fitted curve and its provenance as JSON."""
    path = Path(path) if path is not None else CHECKPOINT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model.as_dict() | report, indent=2) + "\n")
    return path


def train(output: Path | None = None) -> tuple[DamageModel, dict]:
    """Fit the curve end to end and write the checkpoint."""
    paths, damages = load_labelled_files()
    if len(paths) != EXPECTED_TRAIN_FILES:
        print(f"note: {len(paths)} training files, expected {EXPECTED_TRAIN_FILES}")

    started = time.perf_counter()
    cycles = extract_all(paths)
    print(
        f"{len(paths)} files -> {sum(len(c) for c in cycles):,} cycles "
        f"in {time.perf_counter() - started:.1f}s"
    )

    coarse = coarse_grid()
    located = fit(damage_sums(cycles, coarse), coarse, damages)
    exponents = fine_grid(located.exponent)
    sums = damage_sums(cycles, exponents)
    model = fit(sums, exponents, damages)

    fit_mape = mape(damages, predict_from_sums(model, sums, exponents))
    cv_errors = cross_validate(sums, exponents, damages)
    report = build_report(
        damages, fit_mape, cv_errors, [path.name for path in paths]
    )

    written = write_checkpoint(model, report, output)
    print(
        f"m={model.exponent:g}  C={model.coefficient:.6g}\n"
        f"fit MAPE {report['fit_mape']:.2%}  "
        f"LOO MAPE {report['cv_mape']:.2%}  score {report['cv_score']:.4f}\n"
        f"worst: "
        + ", ".join(f"{name} {error:.1%}" for name, error in report["worst_files"].items())
        + f"\nwrote {written}"
    )
    return model, report


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit the SHM fatigue-damage curve.")
    parser.add_argument(
        "--output", type=Path, default=None, help=f"Checkpoint path (default {CHECKPOINT_PATH})."
    )
    arguments = parser.parse_args()
    try:
        train(arguments.output)
    except Exception as error:
        raise SystemExit(f"SHM training failed: {error}") from error


if __name__ == "__main__":
    main()
