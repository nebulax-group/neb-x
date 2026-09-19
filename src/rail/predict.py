"""Rail test files -> the submission rows, and the CSV on disk.

``predict`` is the whole integration contract: the app hands it staged paths and
renders what comes back (``src/app/services.py``). Only this module and train.py
write under outputs/.

The checkpoint is read inside ``predict`` rather than at import, because the app
decides whether a subsystem exists by importing this module -- an untrained rail
must not take the app down at startup. The checkpoint path is derived from the
same two owned constants train.py derives it from rather than imported, so
nothing in the prediction path depends on the fitting path.
"""

import argparse
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from src.common.config import MODEL_DIRS, PREDICTION_PATHS, TEST_PATHS
from src.common.io import list_data_files
from src.rail import config, dataset, features

FILE_ID, PREDICTION = config.PREDICTION_COLUMNS
CHECKPOINT_PATH = MODEL_DIRS[config.SUBSYSTEM_KEY] / config.CHECKPOINT_NAME
DEFAULT_OUTPUT_PATH = PREDICTION_PATHS[config.SUBSYSTEM_KEY]


def load_checkpoint() -> dict:
    """The fitted classifier. A missing one is a setup error, not a default.

    Rail used to answer constant ``Normal`` here, on the argument that the
    majority class is a real 0.308 macro F1 rather than a fabricated number and
    keeps the app answering during a demo. It is still all of that, and it is
    also indistinguishable from a working model everywhere it matters: the app
    renders 68 rows, ``src/submission/generate.py`` writes them, and
    ``src/submission/validate.py`` passes them, none of them able to tell that
    no model produced any of it. The warning existed only in this module's
    ``main()``, which the submission path never calls. Door and SHM both refuse
    for the same reason (``src/shm/predict.py``), so rail refuses too.

    A checkpoint fitted on different columns raises on the same argument:
    predicting through it would silently score whatever the mismatched columns
    happen to mean.
    """
    if not CHECKPOINT_PATH.exists():
        raise FileNotFoundError(
            f"No rail checkpoint at {CHECKPOINT_PATH}. Fit one with: python -m src.rail.train"
        )

    with CHECKPOINT_PATH.open("rb") as handle:
        checkpoint = pickle.load(handle)
    # Both guards, because neither catches the other: the names miss a retuned
    # Welch window or a swapped pair of rails, and the fingerprint misses a
    # renamed or reordered column.
    stale = tuple(checkpoint.get("columns", ())) != features.FEATURE_NAMES or (
        checkpoint.get("fingerprint") != config.FEATURE_FINGERPRINT
    )
    if stale:
        raise ValueError(
            f"{CHECKPOINT_PATH.name} was fitted on different features than "
            "features.py now builds. Re-run: python -m src.rail.train --refresh"
        )
    return checkpoint


def feature_matrix(inputs: list[Path]) -> np.ndarray:
    """Featurise each input in the order given, one recording at a time."""
    return np.vstack([features.extract(dataset.load_recording(path)) for path in inputs])


def predict(inputs: list[Path], checkpoint: dict | None = None) -> pd.DataFrame:
    """Turn held-out rail inputs into exactly the submission rows for this subsystem.

    ``file_id`` is the source filename verbatim, extension included, echoed from
    disk rather than rebuilt: the organisers match on it exactly, and the held-out
    names are ``Test1.csv`` .. ``Test68.csv`` -- capital T, not zero-padded.
    """
    if not inputs:
        raise ValueError("No rail input files to predict on.")

    checkpoint = load_checkpoint() if checkpoint is None else checkpoint
    predicted = checkpoint["estimator"].predict(feature_matrix(inputs))
    return pd.DataFrame({FILE_ID: [path.name for path in inputs], PREDICTION: predicted})


def write_predictions(frame: pd.DataFrame, path: Path | None = None) -> Path:
    """Write the submission CSV. The index is never written -- a stray leading
    column breaks the schema."""
    path = DEFAULT_OUTPUT_PATH if path is None else Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def main() -> None:
    """Run the model over one file or folder and write the predictions CSV."""
    parser = argparse.ArgumentParser(
        description="Classify each rail recording as Normal, Side I or Side II."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=TEST_PATHS[config.SUBSYSTEM_KEY],
        help="Rail data file or folder of files; defaults to the rail test folder.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Destination CSV; defaults to {DEFAULT_OUTPUT_PATH}.",
    )
    args = parser.parse_args()

    try:
        frame = predict(list_data_files(args.input))
        output_path = write_predictions(frame, args.output)
    # A checkpoint written by another version of this package fails in its own
    # way -- a missing key, an unpickling error, a class sklearn has since moved
    # -- and every one of those has to read as a sentence, not a traceback.
    except (OSError, ValueError, KeyError, AttributeError, ImportError, pickle.UnpicklingError) as error:
        raise SystemExit(f"Rail prediction failed: {error}")

    counts = frame[PREDICTION].value_counts()
    print(f"Wrote {len(frame)} rail predictions to {output_path}")
    print("  " + "  ".join(f"{label} {counts.get(label, 0)}" for label in config.LABELS))


if __name__ == "__main__":
    main()
