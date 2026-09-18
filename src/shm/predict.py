"""Predict cumulative fatigue damage per SHM file and write the submission CSV.

Each input history is reduced to rainflow cycles and run through the S-N curve
fitted by ``train.py``. The checkpoint is read inside ``predict`` rather than at
import: the app decides whether a subsystem is available by importing this
module, so an untrained model must surface as a sentence when someone runs it,
not as a crash when the app starts.

There is no fall back to a constant when the checkpoint is missing. A silent
default would submit plausible-looking numbers that no model produced, which is
worse than a prediction that plainly refuses to run.
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from src.common.config import PREDICTION_PATHS
from src.common.io import list_data_files

from .config import CHECKPOINT_PATH, PREDICTION_COLUMNS, SUBSYSTEM_KEY
from .dataset import list_test_files, read_stress_series
from .features import extract_cycles
from .model import DamageModel

DEFAULT_OUTPUT_PATH = PREDICTION_PATHS[SUBSYSTEM_KEY]


def load_model(path: Path | None = None) -> DamageModel:
    """Read the fitted S-N curve, ignoring the provenance stored alongside it."""
    path = CHECKPOINT_PATH if path is None else Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"No SHM model at {path}. Fit one with: python -m src.shm.train"
        )
    return DamageModel.from_dict(json.loads(path.read_text()))


def predict(inputs: list[Path], model: DamageModel | None = None) -> pd.DataFrame:
    """Turn held-out SHM inputs into exactly the submission rows for this subsystem.

    ``file_id`` is the source filename verbatim, extension included, echoed
    from disk rather than rebuilt: the organisers match on it exactly.
    """
    if not inputs:
        raise ValueError("No SHM input files to predict on.")

    model = load_model() if model is None else model
    rows = [
        (path.name, model.predict(extract_cycles(read_stress_series(path))))
        for path in inputs
    ]
    return pd.DataFrame(rows, columns=list(PREDICTION_COLUMNS))


def write_predictions(frame: pd.DataFrame, path: Path | None = None) -> Path:
    """Write the submission CSV, defaulting to ``outputs/predictions/shm_predictions.csv``.

    The index is never written; a stray leading column breaks the schema.
    """
    path = DEFAULT_OUTPUT_PATH if path is None else Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def main() -> None:
    """Run the model over one file or folder and write the predictions CSV."""
    parser = argparse.ArgumentParser(
        description="Predict SHM cumulative fatigue damage for each input file."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="SHM data file or folder of files; defaults to the SHM test folder.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Destination CSV; defaults to {DEFAULT_OUTPUT_PATH}.",
    )
    args = parser.parse_args()

    try:
        inputs = list_test_files() if args.input is None else list_data_files(args.input)
        frame = predict(inputs)
        output_path = write_predictions(frame, args.output)
    except (OSError, ValueError) as error:
        raise SystemExit(f"SHM prediction failed: {error}")

    print(f"Wrote {len(frame)} SHM predictions to {output_path}")


if __name__ == "__main__":
    main()
