"""Present a finished prediction: what was run and the detailed rows.

Rendering only. The frame arrives already in its subsystem's submission schema;
nothing here inspects or reshapes its columns. The pieces are drawn separately
because the result area shows different ones in each of its two modes; which
appear where is decided in ``src/app/ui/assessment.py``. A run that produced no
frame at all is ``src/app/ui/failure.py``, not a state of this file.
"""

from html import escape

import pandas as pd
import streamlit as st

from src.app.config import READOUT_CAPTIONS

# Left-aligned at column zero on purpose: st.markdown reads four leading spaces as
# an indented code block and would print this markup instead of rendering it.
_READOUT = """<dl class="nx-readout">
<div><dt>{system_caption}</dt><dd>{system}</dd></div>
<div><dt>{rows_caption}</dt><dd>{rows}</dd></div>
</dl>"""


def render_readout(frame: pd.DataFrame, subsystem_label: str) -> None:
    """Say what was run and how many assessment rows were returned."""
    st.markdown(
        _READOUT.format(
            system=escape(subsystem_label),
            rows=len(frame),
            **READOUT_CAPTIONS,
        ),
        unsafe_allow_html=True,
    )


def render_table(frame: pd.DataFrame) -> None:
    """Show the submission rows exactly as they will be written."""
    st.dataframe(frame, width="stretch", hide_index=True)
