"""One section head, used wherever the page starts a new stage of the flow.

Shared by the board and the results so the two cannot drift apart in type or
spacing; the copy itself comes from ``src/app/config.py``.
"""

from html import escape

import streamlit as st

# Left-aligned at column zero on purpose: st.markdown reads four leading spaces as
# an indented code block and would print this markup instead of rendering it.
_TEMPLATE = """<div class="nx-section">
<h2 class="nx-section-title">{title}</h2>
{standfirst}
</div>"""


def render(title: str, standfirst: str | None = None) -> None:
    """Draw a section head, with an optional sentence under it."""
    st.markdown(
        _TEMPLATE.format(
            title=escape(title),
            standfirst=(
                f'<p class="nx-section-standfirst">{escape(standfirst)}</p>'
                if standfirst
                else ""
            ),
        ),
        unsafe_allow_html=True,
    )
