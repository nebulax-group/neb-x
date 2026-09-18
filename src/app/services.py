"""Bridge the app to the subsystem predictors; no UI, feature or model code.

Every subsystem exposes one entry point, ``src.<subsystem>.predict.predict``,
taking input paths and returning that subsystem's submission rows. Nothing here
knows what any of them does with those files.
"""

import importlib
import tempfile
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import pandas as pd

from src.app.config import SUBSYSTEM_LABELS, UPLOAD_DIR_PREFIX
from src.common.config import PREDICTION_FILENAMES

Predictor = Callable[[list[Path]], pd.DataFrame]


class SubsystemUnavailable(RuntimeError):
    """Raised when a subsystem's predict module cannot be imported."""


def _require_known(subsystem: str) -> None:
    if subsystem not in SUBSYSTEM_LABELS:
        known = ", ".join(SUBSYSTEM_LABELS)
        raise ValueError(f"Unknown subsystem: {subsystem!r}. Expected one of {known}.")


def _read_upload(upload: Any) -> bytes:
    for method_name in ("getbuffer", "read"):
        method = getattr(upload, method_name, None)
        if callable(method):
            return bytes(method())
    name = getattr(upload, "name", upload)
    raise TypeError(f"Upload {name!r} exposes neither getbuffer() nor read().")


def load_predictor(subsystem: str) -> Predictor:
    """Return that subsystem's ``predict`` function.

    Raises ``SubsystemUnavailable`` when the module is missing or incomplete.
    """
    _require_known(subsystem)
    # Imported on demand rather than at module scope: the four subsystems land
    # at different times, so an absent or half-written one must fail only when
    # a user picks it, never take the whole app down at startup.
    try:
        module = importlib.import_module(f"src.{subsystem}.predict")
        return module.predict
    except (ImportError, AttributeError) as exc:
        raise SubsystemUnavailable(
            f"The {SUBSYSTEM_LABELS[subsystem]} predictor is not available yet ({exc})."
        ) from exc


def is_available(subsystem: str) -> bool:
    """Whether that subsystem's predictor imports right now."""
    try:
        load_predictor(subsystem)
    except SubsystemUnavailable:
        return False
    return True


def stage_uploads(uploads: Iterable[Any]) -> list[Path]:
    """Write uploaded files into a fresh temporary directory and return them.

    Upload objects are duck-typed on ``.name`` and ``.getbuffer()``/``.read()``
    so this module never imports the UI framework.
    """
    uploads = list(uploads)
    if not uploads:
        raise ValueError("No files were uploaded.")

    directory = Path(tempfile.mkdtemp(prefix=UPLOAD_DIR_PREFIX))
    staged: list[Path] = []
    for upload in uploads:
        # The submitted file_id is the source filename exactly as shipped, so the
        # name is carried through unchanged; renaming here scores that subsystem
        # zero. Only a directory component, which a browser never sends, is dropped.
        path = directory / Path(upload.name).name
        path.write_bytes(_read_upload(upload))
        staged.append(path)
    return staged


def run_prediction(subsystem: str, inputs: list[Path]) -> pd.DataFrame:
    """Run one subsystem's predictor over the given files and return its rows."""
    if not inputs:
        raise ValueError("Select at least one input file before running a prediction.")
    return load_predictor(subsystem)(list(inputs))


def prediction_filename(subsystem: str) -> str:
    """Return the submission filename the predictions must be downloaded as."""
    _require_known(subsystem)
    return PREDICTION_FILENAMES[subsystem]
