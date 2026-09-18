"""Check a prediction CSV against the schema in reference/submission_format/.

Run as ``python -m src.submission.validate <csv> [--inputs <folder>]``.

Every check here catches a failure that scores zero while the file still looks
correct when opened: a renamed column, a stray index column, a ``file_id`` that
was rebuilt rather than echoed. The model is not re-run by the organisers, so
the CSV is the whole submission and nothing downstream will notice.

Problems are returned rather than raised, because a caller wants all of them at
once and not just the first. The command line turns a non-empty list into a
failure; no caller gets a quiet pass.
"""

import argparse
from pathlib import Path

import pandas as pd

from src.common.config import PREDICTION_FILENAMES
from src.common.io import list_data_files, read_table

from .schema import Schema, for_file


def _read(path: Path) -> pd.DataFrame:
    """Read the CSV as text.

    Every column is read as a string and empty cells are kept as empty strings:
    pandas would otherwise turn ACV's ``03`` into the number 3 and a blank cell
    into NaN, hiding the two failures this module exists to catch.
    """
    return read_table(path, dtype=str, keep_default_na=False)


def _check_columns(frame: pd.DataFrame, schema: Schema) -> list[str]:
    found = tuple(frame.columns)
    if found == schema.columns:
        return []

    problems = []
    missing = [column for column in schema.columns if column not in found]
    unexpected = [column for column in found if column not in schema.columns]
    if missing:
        problems.append(f"Missing column(s): {', '.join(missing)}.")
    if unexpected:
        # An index written by to_csv arrives as an unnamed column, which is the
        # single most common way a valid-looking file breaks the schema. Only say
        # so when that is what happened, or the advice misdirects a typo.
        hint = (
            " Write the CSV with index=False."
            if any(column.startswith("Unnamed:") for column in unexpected)
            else ""
        )
        problems.append(f"Unexpected column(s): {', '.join(unexpected)}.{hint}")
    if not missing and not unexpected:
        problems.append(
            f"Columns are in the wrong order: found {', '.join(found)}, "
            f"expected {', '.join(schema.columns)}."
        )
    return problems


def _check_cells(frame: pd.DataFrame, schema: Schema) -> list[str]:
    problems = []
    for column in schema.columns:
        if column not in frame.columns:
            continue
        blank = frame.index[frame[column].astype(str).str.strip() == ""]
        if len(blank):
            rows = ", ".join(str(int(row) + 2) for row in blank[:5])
            problems.append(f"Column {column!r} is empty on row(s) {rows}.")
    return problems


def _check_ids(frame: pd.DataFrame, schema: Schema, inputs: Path | None) -> list[str]:
    """Check the id column against the files it is supposed to name."""
    if schema.id_column is None or schema.id_column not in frame.columns:
        return []

    problems = []
    ids = frame[schema.id_column].astype(str)
    duplicated = sorted(set(ids[ids.duplicated()]))
    if duplicated:
        problems.append(f"Duplicate {schema.id_column}: {', '.join(duplicated[:5])}.")

    if inputs is None:
        return problems

    # The organisers match on the source filename exactly, so a lowercased or
    # rebuilt name scores this subsystem nothing even though every value is right.
    expected = {path.name for path in list_data_files(inputs)}
    written = set(ids)
    if absent := sorted(expected - written):
        problems.append(f"No row for input file(s): {', '.join(absent[:5])}.")
    if extra := sorted(written - expected):
        problems.append(
            f"{schema.id_column} value(s) not among the input files: {', '.join(extra[:5])}. "
            "Echo the filename read from disk rather than rebuilding it."
        )
    return problems


def validate(path: str | Path, inputs: str | Path | None = None) -> list[str]:
    """Check one prediction CSV and return every problem found, or an empty list.

    ``inputs`` is the folder or file the predictions were made from. Given it,
    the id column is checked against the real filenames, which is the check that
    catches a rebuilt ``file_id``.
    """
    path = Path(path)
    if not path.exists():
        return [f"No such file: {path}."]
    if not path.is_file():
        return [f"Not a file: {path}."]

    try:
        schema = for_file(path)
    except ValueError as error:
        return [str(error)]

    try:
        frame = _read(path)
    except (OSError, ValueError) as error:
        return [f"Could not read {path.name}: {error}"]

    problems = _check_columns(frame, schema)
    if frame.empty:
        problems.append(f"{path.name} has a header but no rows.")
        return problems

    problems += _check_cells(frame, schema)
    problems += _check_ids(frame, schema, Path(inputs) if inputs is not None else None)
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check a prediction CSV against reference/submission_format/."
    )
    parser.add_argument("csv", type=Path, help=f"One of: {', '.join(sorted(PREDICTION_FILENAMES.values()))}")
    parser.add_argument(
        "--inputs",
        type=Path,
        default=None,
        help="Folder of test files the predictions were made from, to check file_id against.",
    )
    arguments = parser.parse_args()

    try:
        problems = validate(arguments.csv, arguments.inputs)
    except Exception as error:
        raise SystemExit(f"Validation could not run: {error}") from error

    if problems:
        raise SystemExit(
            f"{arguments.csv.name} is not submittable:\n"
            + "\n".join(f"  - {problem}" for problem in problems)
        )
    print(f"{arguments.csv.name} matches the submission schema.")


if __name__ == "__main__":
    main()
