"""Bridge the app to the subsystem predictors; no UI, feature or model code.

Every subsystem exposes one entry point, ``src.<subsystem>.predict.predict``,
taking input paths and returning that subsystem's submission rows. Nothing here
knows what any of them does with those files.

A subsystem may also expose ``src.<subsystem>.explain.explain`` over the same
inputs, returning panels that say how it reached those rows. That one is optional:
a subsystem without it renders its table alone. Panels are plain dicts so the app
can draw them without importing a subsystem, keeping the rule that the app never
branches on which one is selected — it asks for a capability, not for a name.

Each panel carries ``kind``, ``title``, an optional one-line ``caption`` and an
optional ``subject`` naming the file it describes. ``kind`` chooses the rest:

``verdict``  ``headline``: the answer in a few words. ``severity``: ``clear``,
             ``caution`` or ``danger``. ``detail``: one short line. No ``title``.
             Optional ``recommendation``: a dict with ``title`` and ``steps``.
``metrics``  ``items``: ``label``, ``value`` (already formatted), ``detail``.
``bullet``   ``rows``: ``label``, ``value``, ``detail``; plus ``target`` and
             ``target_label`` for the threshold every row is measured against.
``bars``     ``rows``: ``label``, ``value`` as a 0-1 share, ``detail``; plus
             ``value_title`` for the axis.
``line``     ``points``: parallel ``(x, y)`` lists; plus ``x_title``, ``y_title``.
``strip``    ``cells``: ``label``, ``state`` (a severity, as above), ``detail``, in
             the order they happened; plus ``legend``: ``state``, ``label``.
             Cells may supply ``title``, ``subtitle``, ``status`` and ``fields``
             (``label``, ``value``, ``detail``) for a structured selection readout.

``severity`` is the one judgement the app will not make for itself. The palette
reserves three colours for it and paints whichever the subsystem names; what counts
as a caution is a question about doors or fatigue that only a subsystem can answer.

``verdict`` panels are the answer, and the rest are the workings, so ``split_panels``
separates them and the two are shown in different places. A subsystem still returns
one flat list, and puts the panel that best answers the question first among the
workings: that is the one shown beside the verdict without anyone clicking.

A run that raises instead of returning crosses the same bridge, so ``describe_failure``
turns whatever was raised into a ``Failure``: a ``kind``, the sentence behind it, and
the uploaded files it named. The kinds are told apart by the exception type and
never by which subsystem raised it, which keeps the page's account of a failure as
subsystem-blind as its account of a result.
"""

import functools
import hashlib
import importlib
import re
import shutil
import tempfile
import zipfile
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, NamedTuple

import pandas as pd

from src.app.config import (
    FAILURE_INTERNAL,
    FAILURE_MISMATCH,
    FAILURE_UNAVAILABLE,
    FAILURE_UNREADABLE,
    SUBSYSTEM_LABELS,
    UPLOAD_DIR_PREFIX,
)
from src.common.config import PREDICTION_FILENAMES, XLSX_EXTENSION

Predictor = Callable[[list[Path]], pd.DataFrame]
Explainer = Callable[[list[Path]], list[dict[str, Any]]]

VERDICT_KIND = "verdict"

# A file that never parsed is a different problem for the reader than one that parsed
# into a shape the subsystem does not read: the first is fixed at the export that made
# it, the second by choosing a different system. These are the errors raised before any
# subsystem has looked at a column, so the split costs the app no knowledge of one.
_UNREADABLE_ERRORS = (
    UnicodeDecodeError,
    zipfile.BadZipFile,
    pd.errors.EmptyDataError,
    pd.errors.ParserError,
)


class SubsystemUnavailable(RuntimeError):
    """Raised when a subsystem's predict module cannot be imported."""


class AssessmentFailed(RuntimeError):
    """A processing error after upload validation; do not blame the input layout."""


class Failure(NamedTuple):
    """Why a run produced no reading: its category and the evidence."""

    kind: str
    reason: str
    subjects: tuple[str, ...]


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


# Qualified rather than imported bare: this package also holds a module called cache,
# and the two mean different things.
@functools.cache
def _staging_root() -> Path:
    """The one directory this process stages into, made when first asked for."""
    return Path(tempfile.mkdtemp(prefix=UPLOAD_DIR_PREFIX))


def upload_digest(uploads: Iterable[Any]) -> str:
    """A stable id for exactly these files holding exactly this content.

    What was uploaded is the whole of what a reading depends on, so this is what
    the app keys its cache on. Neither a staged path nor an upload object will do:
    the browser hands over a new object on every rerun, and the same files staged
    twice would be two different paths.
    """
    digest = hashlib.sha256()
    for upload in uploads:
        # A filename cannot hold a null byte, so the separator is what keeps one
        # file's name from running into the next file's content in the hash.
        digest.update(Path(upload.name).name.encode("utf-8") + b"\0")
        payload = _read_upload(upload)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def stage_uploads(uploads: Iterable[Any]) -> list[Path]:
    """Write the uploaded files somewhere a subsystem can read them, and return them.

    The directory is named after the content, so staging the same files again lands
    in the same place instead of leaving another temporary directory behind.

    Upload objects are duck-typed on ``.name`` and ``.getbuffer()``/``.read()``
    so this module never imports the UI framework.
    """
    uploads = list(uploads)
    if not uploads:
        raise ValueError("No files were uploaded.")
    names = [Path(upload.name).name for upload in uploads]
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError("Two uploads have the same filename. Remove the duplicate and assess each recording separately.")

    directory = _staging_root() / upload_digest(uploads)
    directory.mkdir(parents=True, exist_ok=True)
    staged: list[Path] = []
    for upload in uploads:
        # The submitted file_id is the source filename exactly as shipped, so the
        # name is carried through unchanged; renaming here scores that subsystem
        # zero. Only a directory component, which a browser never sends, is dropped.
        path = directory / Path(upload.name).name
        path.write_bytes(_read_upload(upload))
        staged.append(path)
    return staged


def discard_staged(batch: str) -> None:
    """Remove the copy staged for one set of files, if it is still on disk.

    The deployed filesystem is held in memory, so a session that works through several
    large batches would otherwise carry every one of them until the process ends.
    """
    shutil.rmtree(_staging_root() / batch, ignore_errors=True)


def run_prediction(subsystem: str, inputs: list[Path]) -> pd.DataFrame:
    """Run one subsystem's predictor over the given files and return its rows."""
    if not inputs:
        raise ValueError("Select at least one input file before running a prediction.")
    validate_inputs(subsystem, inputs)
    predictor = load_predictor(subsystem)
    try:
        return predictor(list(inputs))
    except (FileNotFoundError, ImportError) as exc:
        raise SubsystemUnavailable(str(exc)) from exc
    except Exception as exc:
        raise AssessmentFailed(str(exc)) from exc


def validate_inputs(subsystem: str, inputs: list[Path]) -> None:
    """Ask an optional subsystem validator to check uploads before model loading.

    Schema knowledge stays beside each dataset reader. Missing validators are a
    supported capability gap; broken imports inside one are setup failures.
    """
    _require_known(subsystem)
    for path in inputs:
        if path.suffix.lower() == XLSX_EXTENSION:
            # A renamed CSV has a supported suffix but is not an Excel workbook.
            # Check the container so pandas' ambiguous ValueError is not presented
            # as a subsystem/schema mismatch.
            with zipfile.ZipFile(path) as workbook:
                if "[Content_Types].xml" not in workbook.namelist() or "xl/workbook.xml" not in workbook.namelist():
                    raise zipfile.BadZipFile(f"{path.name} is not an XLSX workbook. Export it again from its source.")
    module_name = f"src.{subsystem}.validate"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return
        raise SubsystemUnavailable(str(exc)) from exc
    except ImportError as exc:
        raise SubsystemUnavailable(str(exc)) from exc
    try:
        module.validate(list(inputs))
    except ImportError as exc:
        raise SubsystemUnavailable(str(exc)) from exc


def load_explainer(subsystem: str) -> Explainer | None:
    """Return that subsystem's ``explain`` function, or None if it has none.

    Absence is a normal answer here, unlike a missing predictor: three of the four
    subsystems may never gain one, and the app must render their results anyway.
    """
    _require_known(subsystem)
    try:
        module = importlib.import_module(f"src.{subsystem}.explain")
        return module.explain
    except (ImportError, AttributeError):
        return None


def explain_prediction(subsystem: str, inputs: list[Path]) -> list[dict[str, Any]]:
    """Panels explaining a prediction, or an empty list if none are offered."""
    explainer = load_explainer(subsystem)
    if explainer is None:
        return []
    if not inputs:
        raise ValueError("Select at least one input file before running a prediction.")
    return explainer(list(inputs))


def split_panels(
    panels: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separate the verdicts from the workings, each keeping its original order."""
    verdicts = [panel for panel in panels if panel.get("kind") == VERDICT_KIND]
    workings = [panel for panel in panels if panel.get("kind") != VERDICT_KIND]
    return verdicts, workings


def _sentence(exc: BaseException) -> str:
    """The exception's own words, without the quotes ``str`` would put round them.

    ``str(KeyError("..."))`` is the repr of its argument, so a message written as a
    sentence arrives on screen wearing double quotes and reads as a quotation of
    someone. Every exception the subsystems raise carries one string and no more.
    """
    args = getattr(exc, "args", ())
    if len(args) == 1 and isinstance(args[0], str):
        return args[0]
    return str(exc)


def _kind(exc: BaseException) -> str:
    if isinstance(exc, (SubsystemUnavailable, FileNotFoundError, ImportError)):
        return FAILURE_UNAVAILABLE
    if isinstance(exc, _UNREADABLE_ERRORS):
        return FAILURE_UNREADABLE
    if isinstance(exc, (ValueError, KeyError)):
        return FAILURE_MISMATCH
    return FAILURE_INTERNAL


def describe_failure(exc: BaseException, uploads: Iterable[Any] = ()) -> Failure:
    """Classify what a run raised, and name its files without naming their paths.

    ``stage_uploads`` writes every upload into a temporary directory of this module's
    own making, so a subsystem that quotes the path it was handed quotes that whole
    directory back at the user. Only the filename was ever theirs, so the directory
    is taken out again here rather than shown to someone who cannot act on it.

    Files the reason names come first in ``subjects``: with sixteen segments uploaded,
    the one that stopped the run is the one worth reading first.
    """
    names = tuple(Path(getattr(upload, "name", upload)).name for upload in uploads)
    reason = _sentence(exc)
    for name in names:
        reason = re.sub(rf"\S*[\\/]{re.escape(name)}", name, reason)
    named = tuple(name for name in names if name in reason)
    rest = tuple(name for name in names if name not in named)
    return Failure(_kind(exc), reason, named + rest)


def prediction_filename(subsystem: str) -> str:
    """Return the submission filename the predictions must be downloaded as."""
    _require_known(subsystem)
    return PREDICTION_FILENAMES[subsystem]


def review_report(subsystem: str, inputs: list[Path], reading: Any) -> dict:
    """Ask the subsystem which findings and evidence belong in a maintenance handoff.

    The report carries recipient, summary, method, limitations, findings (small
    tabular records), actions and an optional chart (title, unit, rows). It never
    carries raw sensor samples or a trained model. Each subsystem owns selection.
    """
    _require_known(subsystem)
    module = importlib.import_module(f"src.{subsystem}.handoff")
    return module.build(inputs, reading.frame, reading.panels)
