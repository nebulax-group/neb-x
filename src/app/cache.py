"""Run a reading once per set of files, rather than once per interaction.

Streamlit re-executes the whole script on every click, so a predictor called at
flow level runs again each time the view is toggled or the explanation stepped.
On sixteen SHM files that is seconds of the same arithmetic per click, and the
answer cannot have changed: the files have not.

The key is a digest of the uploaded bytes and their names. A staged path will not
do, because the same files staged twice are two directories; an upload object will
not do either, because the browser hands over a new one on every rerun.

The prediction and the explanation are cached apart. The explanation is optional
and allowed to fail, and one shared entry would mean a failed chart taking the
prediction down with it.
"""

from pathlib import Path
from typing import Any, NamedTuple

import pandas as pd
import streamlit as st

from src.app import services
from src.app.config import CACHE_MAX_READINGS


class Reading(NamedTuple):
    """One subsystem's answer for one set of files, and its own account of it."""

    frame: pd.DataFrame
    panels: list[dict[str, Any]]
    explain_failure: str | None


# ``_uploads`` is left out of the cache key by that leading underscore, which is
# how st.cache_data is told to ignore an argument. It is the very content ``batch``
# is a digest of, and hashing a large upload twice would cost what this avoids.
@st.cache_data(show_spinner=False, max_entries=CACHE_MAX_READINGS)
def _staged(batch: str, _uploads: list[Any]) -> list[Path]:
    return services.stage_uploads(_uploads)


@st.cache_data(show_spinner=False, max_entries=CACHE_MAX_READINGS)
def _prediction(subsystem: str, batch: str, _uploads: list[Any]) -> pd.DataFrame:
    return services.run_prediction(subsystem, _staged(batch, _uploads))


@st.cache_data(show_spinner=False, max_entries=CACHE_MAX_READINGS)
def _explanation(
    subsystem: str, batch: str, _uploads: list[Any]
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        return services.explain_prediction(subsystem, _staged(batch, _uploads)), None
    except Exception as exc:
        # The failure is cached with the same key as a success would be, so a
        # subsystem whose explainer is broken is asked once rather than on every
        # click. The prediction is a separate entry and is not touched by this.
        return [], str(exc)


def reading(subsystem: str, uploads: list[Any]) -> Reading:
    """The answer for these files, computed the first time it is asked for.

    Whatever the predictor raises is raised here, and nothing is cached when it
    does, so the next attempt is a real one rather than a replayed failure.
    """
    batch = services.upload_digest(uploads)
    return Reading(
        _prediction(subsystem, batch, uploads),
        *_explanation(subsystem, batch, uploads),
    )
