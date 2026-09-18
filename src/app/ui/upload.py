"""Collect the files the user wants predicted for the system they picked.

Rendering only. Which systems exist and which are selectable is the board's job
(``src/app/ui/board.py``); file discovery, validation and prediction live behind
the services layer. Nothing here knows what any one subsystem expects.
"""

from typing import Any

import streamlit as st

from src.app.config import UPLOAD_HELP, UPLOAD_PROMPT, UPLOAD_WAITING
from src.common.config import SUPPORTED_DATA_EXTENSIONS

# Streamlit matches bare extensions, unlike Path.suffix which keeps the dot.
UPLOAD_TYPES = [extension.removeprefix(".") for extension in SUPPORTED_DATA_EXTENSIONS]


def render_uploader(subsystem_label: str, subsystem: str) -> list[Any]:
    """Collect the user's data files; returns the uploaded objects, possibly empty.

    Keyed per subsystem so switching systems clears the previous batch instead of
    carrying one system's recordings into another system's model.
    """
    uploaded = st.file_uploader(
        UPLOAD_PROMPT.format(label=subsystem_label),
        type=UPLOAD_TYPES,
        accept_multiple_files=True,
        help=UPLOAD_HELP.format(formats=", ".join(SUPPORTED_DATA_EXTENSIONS)),
        key=f"nx-upload-{subsystem}",
    )
    return uploaded or []


def render_waiting(subsystem_label: str) -> None:
    """Say what is expected next, so an empty page never looks like a failure."""
    st.caption(UPLOAD_WAITING.format(label=subsystem_label))
