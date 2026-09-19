"""Collect the files the user wants predicted for the system they picked.

A batch is assessed whole, so the only edit offered is replacing all of it: the
uploader's per-file remove and add controls are hidden in the stylesheet and Clear all
stands in their place. Half a batch swapped underneath an answer would be an answer
about files that are no longer there.

Rendering only. Which systems exist and which are selectable is the board's job
(``src/app/ui/board.py``); file discovery, validation and prediction live behind the
services layer. Nothing here knows what any one subsystem expects.
"""

from collections.abc import Callable
from typing import Any

import streamlit as st

from src.app.config import (
    SUBSYSTEM_LABELS,
    UPLOAD_BATCH,
    UPLOAD_CLEAR,
    UPLOAD_CLEAR_HELP,
    UPLOAD_GENERATION_KEY,
    UPLOAD_HELP,
    UPLOAD_LOCKED,
    UPLOAD_PROMPT,
    UPLOAD_REQUIREMENTS,
    UPLOAD_WAITING,
)
from src.common.config import SUPPORTED_DATA_EXTENSIONS

# Streamlit matches bare extensions, unlike Path.suffix which keeps the dot.
UPLOAD_TYPES = [extension.removeprefix(".") for extension in SUPPORTED_DATA_EXTENSIONS]

_WINDOW_KEY = "nx-upload-window-{subsystem}"
_UPLOADER_KEY = "nx-upload-{subsystem}-{generation}"
_CLEAR_KEY = "nx-clear-{subsystem}"


def _generation(subsystem: str) -> int:
    return st.session_state.get(UPLOAD_GENERATION_KEY, {}).get(subsystem, 0)


def _uploader_key(subsystem: str) -> str:
    return _UPLOADER_KEY.format(subsystem=subsystem, generation=_generation(subsystem))


def files(subsystem: str | None) -> list[Any]:
    """This system's current files, before its uploader is drawn again.

    A keyed widget's value is in session state from the start of the run, which is
    what lets a batch be started in the same pass that draws the system as busy.
    """
    if subsystem is None:
        return []
    return st.session_state.get(_uploader_key(subsystem)) or []


def render_uploader(
    subsystem_label: str,
    subsystem: str,
    locked: bool,
    on_clear: Callable[..., None],
) -> None:
    """Collect the user's data files for one system.

    Each subsystem owns an uploader that stays mounted while switching windows. A
    locked one keeps its files and refuses every control on it, so a batch cannot be
    changed underneath the model reading it.
    """
    st.file_uploader(
        UPLOAD_PROMPT.format(label=subsystem_label),
        type=UPLOAD_TYPES,
        accept_multiple_files=True,
        help=UPLOAD_HELP.format(formats=", ".join(SUPPORTED_DATA_EXTENSIONS)),
        key=_uploader_key(subsystem),
        disabled=locked,
    )
    if locked:
        st.caption(UPLOAD_LOCKED.format(label=subsystem_label))
        return

    st.caption(UPLOAD_REQUIREMENTS[subsystem])
    if files(subsystem):
        st.caption(UPLOAD_BATCH)
        with st.container(key=_CLEAR_KEY.format(subsystem=subsystem)):
            st.button(
                UPLOAD_CLEAR,
                key=f"{_CLEAR_KEY.format(subsystem=subsystem)}-button",
                help=UPLOAD_CLEAR_HELP,
                on_click=on_clear,
                args=(subsystem, st.session_state),
            )


def render_windows(
    selected: str | None,
    available: dict[str, bool],
    locked: dict[str, bool],
    on_clear: Callable[..., None],
) -> None:
    """Mount every uploader to preserve its files, showing only the active window.

    Streamlit file uploaders do not support persist_state. Keeping the native
    widgets mounted preserves their file tiles and the uploaded bytes; hidden windows
    never start a reading.
    """
    hidden = [
        f".st-key-{_WINDOW_KEY.format(subsystem=key)}"
        for key in available
        if key != selected
    ]
    if hidden:
        st.markdown(
            f"<style>{', '.join(hidden)} {{ display: none; }}</style>",
            unsafe_allow_html=True,
        )
    for key, ready in available.items():
        if ready:
            with st.container(key=_WINDOW_KEY.format(subsystem=key)):
                render_uploader(
                    SUBSYSTEM_LABELS[key], key, locked.get(key, False), on_clear
                )


def render_waiting(subsystem_label: str) -> None:
    """Say what is expected next, so an empty page never looks like a failure."""
    st.caption(UPLOAD_WAITING.format(label=subsystem_label))
