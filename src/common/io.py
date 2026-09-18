"""Read raw tables and discover input files without subsystem preprocessing."""

from pathlib import Path
from typing import Any

import pandas as pd

from .config import (
    CSV_EXTENSION,
    DEFAULT_EXCEL_SHEET,
    IGNORED_DATA_FILE_PREFIXES,
    SUPPORTED_DATA_EXTENSIONS,
)


def _check_extension(path: Path) -> None:
    if path.suffix.lower() not in SUPPORTED_DATA_EXTENSIONS:
        supported = ", ".join(SUPPORTED_DATA_EXTENSIONS)
        raise ValueError(f"Unsupported data file: {path}. Expected {supported}.")


def read_table(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Read one CSV or XLSX sheet using pandas' default parsing conventions.

    Pass reader options explicitly when a dataset needs them, for example
    ``header=None``, ``dtype={\"faulty_car\": str}``, or ``sheet_name=\"Sheet1\"``.
    No columns, timestamps or units are interpreted here. CSV chunk iterators
    and multi-sheet Excel reads are excluded so callers always get a DataFrame.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Data file does not exist: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"Expected a data file: {path}")
    _check_extension(path)

    if path.suffix.lower() == CSV_EXTENSION:
        if kwargs.get("chunksize") is not None or kwargs.get("iterator", False):
            raise ValueError("read_table returns one DataFrame; chunked reads are unsupported.")
        return pd.read_csv(path, **kwargs)

    if not isinstance(kwargs.get("sheet_name", DEFAULT_EXCEL_SHEET), (str, int)):
        raise ValueError("sheet_name must select one sheet by name or index.")
    kwargs.setdefault("sheet_name", DEFAULT_EXCEL_SHEET)
    return pd.read_excel(path, **kwargs)


def list_data_files(path: str | Path) -> list[Path]:
    """List CSV/XLSX inputs in filename order, or wrap a single input file.

    Folder discovery is non-recursive so train/test folders stay separate.
    Hidden files and Excel lock files are ignored; source filenames are kept
    unchanged for submission IDs. Missing or empty inputs raise an exception.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Data path does not exist: {path}")
    if path.is_file():
        _check_extension(path)
        return [path]
    if not path.is_dir():
        raise NotADirectoryError(f"Expected a data file or directory: {path}")

    files = sorted(
        (
            item
            for item in path.iterdir()
            if item.is_file()
            and item.suffix.lower() in SUPPORTED_DATA_EXTENSIONS
            and not item.name.startswith(IGNORED_DATA_FILE_PREFIXES)
        ),
        key=lambda item: (item.name.casefold(), item.name),
    )
    if not files:
        raise ValueError(f"No CSV/XLSX data files found in: {path}")
    return files
