"""Present a finished prediction: what was run, the rows themselves, and the download.

Rendering only. The frame arrives already in its subsystem's submission schema;
nothing here inspects or reshapes its columns. The pieces are drawn separately
because the result area shows different ones in each of its two modes; which
appear where is decided in ``src/app/ui/assessment.py``. A run that produced no
frame at all is ``src/app/ui/failure.py``, not a state of this file.
"""

from html import escape

import pandas as pd
import streamlit as st

from src.app.config import DOWNLOAD_LABEL, READOUT_CAPTIONS

# Left-aligned at column zero on purpose: st.markdown reads four leading spaces as
# an indented code block and would print this markup instead of rendering it.
_READOUT = """<dl class="nx-readout">
<div><dt>{system_caption}</dt><dd>{system}</dd></div>
<div><dt>{rows_caption}</dt><dd>{rows}</dd></div>
<div><dt>{output_caption}</dt><dd>{output}</dd></div>
</dl>"""


def render_readout(frame: pd.DataFrame, download_name: str, subsystem_label: str) -> None:
    """Say what was run, over how many rows, and what the download will be called."""
    st.markdown(
        _READOUT.format(
            system=escape(subsystem_label),
            rows=len(frame),
            output=escape(download_name),
            **READOUT_CAPTIONS,
        ),
        unsafe_allow_html=True,
    )


def render_table(frame: pd.DataFrame) -> None:
    """Show the submission rows exactly as they will be written."""
    st.dataframe(frame, width="stretch", hide_index=True)


def render_download(frame: pd.DataFrame, download_name: str, key: str) -> None:
    """Offer the rows as the submission CSV.

    Keyed because both modes of the result area draw this button, and two Streamlit
    widgets of the same type in one run must not share an identity.
    """
    st.download_button(
        DOWNLOAD_LABEL,
        # This file is scored as-is against a fixed column list. Writing the index
        # would add an unnamed first column and invalidate the submission.
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name=download_name,
        mime="text/csv",
        type="primary",
        key=key,
    )
