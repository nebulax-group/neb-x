"""Draw the answer: one card per verdict a subsystem returned.

Rendering only, and it decides nothing. The severity comes from the subsystem and
this file looks up a colour and a word for it; a severity the palette has no colour
for is still drawn, unmarked, rather than dropped or recoloured into one the app
made up. The panel shape is documented in ``src/app/services.py``.
"""

from html import escape
from typing import Any

import streamlit as st

from src.app.config import SEVERITY_WORDS

# Left-aligned at column zero on purpose: st.markdown reads four leading spaces as
# an indented code block and would print this markup instead of rendering it.
_CARD = """<div class="nx-verdict {state}">
<div class="nx-verdict-flag"><span class="nx-verdict-lamp"></span>
<span class="nx-verdict-word">{word}</span>{subject}</div>
<p class="nx-verdict-headline">{headline}</p>
{detail}
</div>"""

_SUBJECT = '<span class="nx-verdict-subject">{subject}</span>'
_DETAIL = '<p class="nx-verdict-detail">{detail}</p>'


def render(panels: list[dict[str, Any]]) -> None:
    """Draw every verdict in order. Silent when there are none."""
    for panel in panels:
        severity = str(panel.get("severity", ""))
        known = severity in SEVERITY_WORDS
        st.markdown(
            _CARD.format(
                # Interpolated into a class attribute, so only a severity the palette
                # already names may reach it; anything else contributes no class.
                state=f"nx-sev-{severity}" if known else "",
                word=escape(SEVERITY_WORDS[severity] if known else severity),
                subject=(
                    _SUBJECT.format(subject=escape(str(subject)))
                    if (subject := panel.get("subject"))
                    else ""
                ),
                headline=escape(str(panel.get("headline", ""))),
                detail=(
                    _DETAIL.format(detail=escape(str(detail)))
                    if (detail := panel.get("detail"))
                    else ""
                ),
            ),
            unsafe_allow_html=True,
        )
