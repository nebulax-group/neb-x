"""Read the prediction schema from the shipped example CSVs. No checking here.

``reference/submission_format/`` is the schema contract as the organisers shipped
it, so the columns are read from those files rather than restated. A subsystem
whose schema we misremember is then impossible: the only way to disagree with
the contract is to edit the contract.

Door and ACV do not share the other two's columns, and nothing here special
cases them. Whatever their example file declares is their schema.
"""

from dataclasses import dataclass
from pathlib import Path

from src.common.config import (
    EXAMPLE_PREDICTION_PATHS,
    FILE_ID_COLUMN,
    PREDICTION_FILENAMES,
)
from src.common.io import read_table


@dataclass(frozen=True)
class Schema:
    """One subsystem's prediction file: its name and its columns, in order."""

    subsystem: str
    filename: str
    columns: tuple[str, ...]

    @property
    def id_column(self) -> str | None:
        """The column naming the source file, when this schema has one.

        Door does not: its rows are segments of one continuous stream, so there
        is nothing to name them after.
        """
        return FILE_ID_COLUMN if FILE_ID_COLUMN in self.columns else None


def for_subsystem(subsystem: str) -> Schema:
    """Read one subsystem's schema off its example CSV."""
    if subsystem not in PREDICTION_FILENAMES:
        known = ", ".join(sorted(PREDICTION_FILENAMES))
        raise ValueError(f"Unknown subsystem: {subsystem!r}. Expected one of {known}.")

    path = EXAMPLE_PREDICTION_PATHS[subsystem]
    if not path.exists():
        raise FileNotFoundError(
            f"No example prediction file at {path}. The schema is read from the "
            "organisers' own examples, so it cannot be checked without them."
        )

    columns = tuple(read_table(path, dtype=str, nrows=0).columns)
    if not columns:
        raise ValueError(f"Example prediction file {path} declares no columns.")
    return Schema(subsystem=subsystem, filename=PREDICTION_FILENAMES[subsystem], columns=columns)


def for_file(path: str | Path) -> Schema:
    """The schema a file's own name commits it to.

    The filename is part of the contract, not a label we choose at packaging
    time, so it is what decides which schema applies.
    """
    name = Path(path).name
    for subsystem, filename in PREDICTION_FILENAMES.items():
        if name == filename:
            return for_subsystem(subsystem)

    expected = ", ".join(sorted(PREDICTION_FILENAMES.values()))
    raise ValueError(f"{name!r} is not a prediction filename. Expected one of {expected}.")
