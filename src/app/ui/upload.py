"""Collect the files the user wants predicted for the system they picked.

Rendering only. Which systems exist and which are selectable is the board's job
(``src/app/ui/board.py``); file discovery, validation and prediction live behind
the services layer. Nothing here knows what any one subsystem expects.
"""

from typing import Any

import streamlit as st

from src.app.config import UPLOAD_HELP, UPLOAD_PROMPT, UPLOAD_REQUIREMENTS, UPLOAD_WAITING
from src.common.config import SUPPORTED_DATA_EXTENSIONS
from src.app.config import SUBSYSTEM_LABELS

# Streamlit matches bare extensions, unlike Path.suffix which keeps the dot.
UPLOAD_TYPES = [extension.removeprefix(".") for extension in SUPPORTED_DATA_EXTENSIONS]


def render_uploader(subsystem_label: str, subsystem: str) -> list[Any]:
    """Collect the user's data files; returns the uploaded objects, possibly empty.

    Each subsystem owns an uploader that stays mounted while switching windows.
    """
    uploaded = st.file_uploader(
        UPLOAD_PROMPT.format(label=subsystem_label),
        type=UPLOAD_TYPES,
        accept_multiple_files=True,
        help=UPLOAD_HELP.format(formats=", ".join(SUPPORTED_DATA_EXTENSIONS)),
        key=f"nx-upload-{subsystem}",
    )
    st.caption(UPLOAD_REQUIREMENTS[subsystem])
    return uploaded or []


def render_windows(selected: str | None, available: dict[str, bool]) -> dict[str, list[Any]]:
    """Mount every uploader to preserve its files, showing only the active window.

    Streamlit file uploaders do not support persist_state. Keeping the native
    widgets mounted preserves their file tiles and removal controls as well as
    the uploaded bytes; hidden windows never run inference.
    """
    hidden = [f".st-key-nx-upload-window-{key}" for key in available if key != selected]
    if hidden:
        st.markdown(f"<style>{', '.join(hidden)} {{ display: none; }}</style>", unsafe_allow_html=True)
    batches = {}
    for key, ready in available.items():
        if ready:
            with st.container(key=f"nx-upload-window-{key}"):
                batches[key] = render_uploader(SUBSYSTEM_LABELS[key], key)
    return batches


def render_waiting(subsystem_label: str) -> None:
    """Say what is expected next, so an empty page never looks like a failure."""
    st.caption(UPLOAD_WAITING.format(label=subsystem_label))
