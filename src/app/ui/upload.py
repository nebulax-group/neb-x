"""Collect what the user wants predicted: which subsystem, and which files.

Rendering only. File discovery, validation and prediction live behind the
services layer; nothing here knows what any one subsystem expects.
"""

from typing import Any

import streamlit as st

from src.app.config import SUBSYSTEM_PROMPT, UPLOAD_HELP, UPLOAD_PROMPT
from src.common.config import SUPPORTED_DATA_EXTENSIONS

# Streamlit matches bare extensions, unlike Path.suffix which keeps the dot.
UPLOAD_TYPES = [extension.removeprefix(".") for extension in SUPPORTED_DATA_EXTENSIONS]


def render_subsystem_picker(labels: dict[str, str]) -> str:
    """Let the user choose a subsystem; returns the subsystem key."""
    return st.selectbox(
        SUBSYSTEM_PROMPT,
        options=list(labels),
        format_func=lambda key: labels[key],
    )


def render_uploader(subsystem_label: str) -> list[Any]:
    """Collect the user's data files; returns the uploaded objects, possibly empty."""
    uploaded = st.file_uploader(
        UPLOAD_PROMPT.format(label=subsystem_label),
        type=UPLOAD_TYPES,
        accept_multiple_files=True,
        help=UPLOAD_HELP.format(formats=", ".join(SUPPORTED_DATA_EXTENSIONS)),
    )
    return uploaded or []
