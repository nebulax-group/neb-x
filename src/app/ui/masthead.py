"""The page masthead: the mark, the product name, and what the tool is for.

Drawn as markup rather than ``st.title`` so the rule, the mark and the type sit
on one baseline. The mark is inline SVG — a length of track seen from above —
because an emoji would render differently on every machine the demo is watched on.
"""

import streamlit as st

from src.app.config import PALETTE

# Left-aligned at column zero on purpose: st.markdown reads four leading spaces as
# an indented code block and would print this markup instead of rendering it.
_TEMPLATE = """<div class="nx-masthead">
<svg class="nx-mark" width="34" height="34" viewBox="0 0 32 32" role="img" aria-label="Track viewed from above">
<g stroke="{sleeper}" stroke-width="1.6" stroke-linecap="square">
<line x1="4" y1="8" x2="28" y2="8"/>
<line x1="4" y1="14" x2="28" y2="14"/>
<line x1="4" y1="20" x2="28" y2="20"/>
<line x1="4" y1="26" x2="28" y2="26"/>
</g>
<g stroke="{rail}" stroke-width="2.4" stroke-linecap="square">
<line x1="11" y1="3" x2="11" y2="30"/>
<line x1="21" y1="3" x2="21" y2="30"/>
</g>
</svg>
<div class="nx-masthead-text">
<span class="nx-eyebrow">{eyebrow}</span>
<h1 class="nx-title">{title}</h1>
</div>
</div>
<p class="nx-standfirst">{standfirst}</p>"""


def render(eyebrow: str, title: str, standfirst: str) -> None:
    """Draw the masthead and the sentence explaining what to do."""
    st.markdown(
        _TEMPLATE.format(
            sleeper=PALETTE["ink-muted"],
            rail=PALETTE["oxide"],
            eyebrow=eyebrow,
            title=title,
            standfirst=standfirst,
        ),
        unsafe_allow_html=True,
    )
