"""Present a finished prediction table, and the two states where there isn't one.

Rendering only. The frame arrives already in its subsystem's submission schema;
nothing here inspects or reshapes its columns.
"""

from html import escape

import pandas as pd
import streamlit as st

from src.app.config import (
    DOWNLOAD_LABEL,
    ERROR_HINT,
    READOUT_CAPTIONS,
    RESULTS_HEADING,
    UNAVAILABLE_MESSAGE,
)
from src.app.ui import section

# Left-aligned at column zero on purpose: st.markdown reads four leading spaces as
# an indented code block and would print this markup instead of rendering it.
_READOUT = """<dl class="nx-readout">
<div><dt>{system_caption}</dt><dd>{system}</dd></div>
<div><dt>{rows_caption}</dt><dd>{rows}</dd></div>
<div><dt>{output_caption}</dt><dd>{output}</dd></div>
</dl>"""


def render_results(frame: pd.DataFrame, download_name: str, subsystem_label: str) -> None:
    """Show the prediction rows and offer them as the submission CSV."""
    section.render(RESULTS_HEADING)
    st.markdown(
        _READOUT.format(
            system=escape(subsystem_label),
            rows=len(frame),
            output=escape(download_name),
            **READOUT_CAPTIONS,
        ),
        unsafe_allow_html=True,
    )
    st.dataframe(frame, width="stretch", hide_index=True)
    st.download_button(
        DOWNLOAD_LABEL,
        # This file is scored as-is against a fixed column list. Writing the index
        # would add an unnamed first column and invalidate the submission.
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name=download_name,
        mime="text/csv",
        type="primary",
    )


def render_unavailable(subsystem_label: str) -> None:
    """Say plainly that this subsystem has no model yet."""
    st.info(UNAVAILABLE_MESSAGE.format(label=subsystem_label))


def render_error(message: str) -> None:
    """Show a failure as a sentence, not a traceback."""
    st.error(f"{message}\n\n{ERROR_HINT}")
