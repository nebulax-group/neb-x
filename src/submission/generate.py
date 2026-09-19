"""Run each subsystem's predictor over its held-out test inputs and write the CSVs.

Run as ``python -m src.submission.generate``.

The prediction files are always produced here, never found. A CSV already sitting
in ``outputs/predictions/`` was left by an earlier run, a different checkpoint or
somebody's browser download, and nothing about it says which, so it is overwritten
— and one belonging to a subsystem that could not run this time is discarded
rather than packaged on the strength of a prediction nobody made.

``src.<sub>.predict.predict`` is the same function ``src/app/services.py`` reaches
through ``run_prediction``, imported by key the same way. The problem statement
asks for predictions "produced by running the held-out test inputs through our own
app", and that is true because this calls that function rather than reimplementing
it. Nothing here may shortcut a subsystem's inference. The app is not imported:
dependencies point one way and nothing imports the app.

Three of the four ways a subsystem can fail to run are ordinary states rather than
faults — ``src/rail/`` may not have landed, ``data/`` is gitignored and absent on
most machines, and a checkpoint under ``outputs/models/`` never travels — so every
one of them is printed with its reason and the other subsystems still build.
Validation is what stops a submission, not this.
"""

import argparse
import importlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.common.config import PREDICTION_PATHS, SUBSYSTEMS, TEST_PATHS
from src.common.io import list_data_files

Predictor = Callable[[list[Path]], pd.DataFrame]


@dataclass(frozen=True)
class Outcome:
    """One subsystem's result: what was written, or why nothing was."""

    subsystem: str
    path: Path | None = None
    rows: int = 0
    reason: str | None = None

    @property
    def written(self) -> bool:
        return self.reason is None


def load_predictor(subsystem: str) -> Predictor:
    """Return ``src.<subsystem>.predict.predict``.

    Imported by key on demand, never at module scope: the four subsystems land at
    different times and an absent one has to be reportable rather than fatal.
    """
    module = importlib.import_module(f"src.{subsystem}.predict")
    return module.predict


def test_inputs(subsystem: str) -> list[Path]:
    """The held-out inputs for one subsystem, in filename order.

    Door's is a single continuous stream and the other three are folders;
    ``list_data_files`` takes either, so nothing here branches on which.
    """
    return list_data_files(TEST_PATHS[subsystem])


def write(frame: pd.DataFrame, path: Path) -> Path:
    """Write the submission CSV, and do nothing else to it.

    ``index=False`` and no other option. The file is scored as-is against a fixed
    column list, so a written index invalidates it and any reordering, renaming or
    reformatting of a column does the same.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def _skip(subsystem: str, path: Path, reason: str) -> Outcome:
    """Record why nothing was written, discarding whatever was already there.

    A file left by an earlier run would otherwise be validated and packaged on the
    strength of a prediction this run could not make.
    """
    if path.exists():
        path.unlink()
        reason = f"{reason}; discarded the stale {path.name}"
    return Outcome(subsystem, reason=reason)


def generate(subsystem: str) -> Outcome:
    """Predict one subsystem's held-out inputs and write its CSV.

    Returns rather than raises. A subsystem that cannot run must not stop the
    others from being submitted, so the caller gets the reason as a value.
    """
    path = PREDICTION_PATHS[subsystem]

    try:
        predictor = load_predictor(subsystem)
    except (ImportError, AttributeError) as error:
        return _skip(subsystem, path, f"no predictor at src.{subsystem}.predict ({error})")

    try:
        inputs = test_inputs(subsystem)
    except (OSError, ValueError) as error:
        return _skip(subsystem, path, f"no test inputs ({error})")

    try:
        frame = predictor(inputs)
    # Every way one subsystem can fail is one subsystem's problem: a checkpoint
    # nobody trained, a column that moved, a file the parser will not read.
    # Narrowing this would turn any one of them into four missing CSVs.
    except Exception as error:
        return _skip(subsystem, path, f"{type(error).__name__}: {error}")

    return Outcome(subsystem, path=write(frame, path), rows=len(frame))


def generate_all() -> list[Outcome]:
    """Every subsystem, in order."""
    return [generate(subsystem) for subsystem in SUBSYSTEMS]


def _report(outcome: Outcome) -> None:
    if not outcome.written:
        print(f"{outcome.subsystem:<5} skipped   {outcome.reason}")
        return
    rows = "1 row" if outcome.rows == 1 else f"{outcome.rows} rows"
    print(f"{outcome.subsystem:<5} {rows:<9} {outcome.path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run every subsystem's predictor over its held-out test inputs and write "
            "the prediction CSVs, overwriting whatever was there."
        )
    )
    parser.parse_args()

    try:
        outcomes = generate_all()
    except OSError as error:
        raise SystemExit(f"Generating predictions failed: {error}")

    for outcome in outcomes:
        _report(outcome)

    written = [outcome for outcome in outcomes if outcome.written]
    if not written:
        raise SystemExit(
            "\nNo predictions could be generated, so there is nothing to validate or package."
        )
    print(f"\n{len(written)} of {len(SUBSYSTEMS)} prediction files generated.")


if __name__ == "__main__":
    main()
