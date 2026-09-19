"""Compute a reading once per set of files, rather than once per interaction.

Streamlit re-executes the whole script on every click, so anything called at flow
level runs again each time the view is toggled or the explanation stepped. On sixteen
SHM files that is seconds of the same arithmetic per click, and the answer cannot have
changed: the files have not.

The key is a digest of the uploaded bytes and their names. A staged path will not do,
because the same files staged twice are two directories; an upload object will not do
either, because the browser hands over a new one on every rerun. Hashing a large batch
is itself expensive, so the digest is memoised against the ids the browser gives each
upload and recomputed only when those change.

``st.cache_data`` cannot hold any of this: these functions are called from a pool
thread, which has no script context for Streamlit's caches to run in.

The prediction and the explanation are kept apart. The explanation is optional and
allowed to fail, and one shared entry would mean a failed chart taking the prediction
down with it.
"""

import threading
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

import pandas as pd

from src.app import services
from src.app.config import CACHE_MAX_READINGS


class Reading(NamedTuple):
    """One subsystem's answer for one set of files, and its own account of it."""

    frame: pd.DataFrame
    panels: list[dict[str, Any]]
    explain_failure: str | None


class _Memo:
    """A bounded least-recently-used store, safe to read and fill from any thread."""

    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._entries: OrderedDict[Any, Any] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Any, build: Callable[[], Any]) -> Any:
        with self._lock:
            if key in self._entries:
                self._entries.move_to_end(key)
                return self._entries[key]
        # Built outside the lock. Holding it across a model would put every other
        # system behind this one, and building the same key twice only wastes the
        # second one. Nothing is kept when the build raises.
        value = build()
        with self._lock:
            self._entries[key] = value
            self._entries.move_to_end(key)
            while len(self._entries) > self._limit:
                self._entries.popitem(last=False)
        return value

    def discard(self, matches: Callable[[Any], bool]) -> None:
        with self._lock:
            for key in [key for key in self._entries if matches(key)]:
                del self._entries[key]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


_DIGESTS = _Memo(CACHE_MAX_READINGS)
_STAGED = _Memo(CACHE_MAX_READINGS)
_PREDICTIONS = _Memo(CACHE_MAX_READINGS)
_EXPLANATIONS = _Memo(CACHE_MAX_READINGS)


def _identity(uploads: list[Any]) -> tuple:
    """Recognise a batch without reading it, where the browser makes that possible.

    Streamlit gives every upload an id that survives a rerun. Anything without one
    falls back to its content, which is correct and costs what this exists to avoid.
    """
    return tuple(
        (getattr(upload, "file_id", None) or services.upload_digest([upload]), upload.name)
        for upload in uploads
    )


def digest(uploads: list[Any]) -> str:
    """The content digest of these files, rehashed only when the batch changes."""
    return _DIGESTS.get(_identity(uploads), lambda: services.upload_digest(uploads))


def staged(batch: str, uploads: list[Any]) -> list[Path]:
    return _STAGED.get(batch, lambda: services.stage_uploads(uploads))


def _explain(subsystem: str, inputs: list[Path]) -> tuple[list[dict[str, Any]], str | None]:
    try:
        return services.explain_prediction(subsystem, inputs), None
    except Exception as exc:
        # Kept under the same key a success would use, so a subsystem whose explainer
        # is broken is asked once rather than on every click. The prediction is a
        # separate entry and is not touched by this.
        return [], str(exc)


def reading(subsystem: str, batch: str, uploads: list[Any]) -> Reading:
    """The answer for these files, computed the first time it is asked for.

    Whatever the predictor raises is raised here, and nothing is kept when it does,
    so the next attempt is a real one rather than a replayed failure.
    """
    inputs = staged(batch, uploads)
    frame = _PREDICTIONS.get(
        (subsystem, batch), lambda: services.run_prediction(subsystem, inputs)
    )
    panels, failure = _EXPLANATIONS.get(
        (subsystem, batch), lambda: _explain(subsystem, inputs)
    )
    return Reading(frame, panels, failure)


def forget(batch: str) -> None:
    """Drop everything held for one set of files, including the copy on disk.

    The digest itself is kept: it is derived from the files and would come back the
    same, and staging simply writes the directory again.
    """
    _STAGED.discard(lambda key: key == batch)
    _PREDICTIONS.discard(lambda key: key[1] == batch)
    _EXPLANATIONS.discard(lambda key: key[1] == batch)
    services.discard_staged(batch)


def clear() -> None:
    """Forget every memoised batch."""
    for memo in (_DIGESTS, _STAGED, _PREDICTIONS, _EXPLANATIONS):
        memo.clear()
