"""The page masthead: the mark, the product name, and what the tool is for.

Drawn as markup rather than ``st.title`` so the rule, the mark and the type sit
on one baseline. The mark is inline SVG — a length of track seen from above —
because an emoji would render differently on every machine the demo is watched on.
"""

import streamlit as st

from src.app.config import PALETTE

# Left-aligned at column zero on purpose: st.markdown reads four leading spaces as
# an indented code block and would print this markup instead of rendering it.
_TEMPLATE = """<div class="nx-rail">
<svg class="nx-mark" width="26" height="26" viewBox="0 0 32 32" role="img" aria-label="Track viewed from above">
<g stroke="{sleeper}" stroke-width="2" stroke-linecap="square">
<line x1="4" y1="8" x2="28" y2="8"/>
<line x1="4" y1="15" x2="28" y2="15"/>
<line x1="4" y1="22" x2="28" y2="22"/>
<line x1="4" y1="29" x2="28" y2="29"/>
</g>
<g stroke="{rail}" stroke-width="2.6" stroke-linecap="square">
<line x1="11" y1="2" x2="11" y2="31"/>
<line x1="21" y1="2" x2="21" y2="31"/>
</g>
</svg>
<span class="nx-wordmark">neb-x</span>
<span class="nx-eyebrow">{eyebrow}</span>
{chip}
</div>
<h1 class="nx-title">{title}</h1>
<p class="nx-standfirst">{standfirst}</p>"""


def render(eyebrow: str, title: str, standfirst: str, chip: str | None = None) -> None:
    """Draw the masthead and the sentence explaining what to do."""
    st.markdown(
        _TEMPLATE.format(
            sleeper=PALETTE["hairline-strong"],
            rail=PALETTE["instrument"],
            eyebrow=eyebrow,
            title=title,
            standfirst=standfirst,
            chip=f'<span class="nx-chip">{chip}</span>' if chip else "",
        ),
        unsafe_allow_html=True,
    )
