"""Present the next steps supplied by a subsystem alongside its assessment."""

from html import escape
from typing import Any

import streamlit as st

from src.app.config import RECOMMENDATION_HEADING

_CARD = """<section class="nx-recommendation" aria-label="{heading}">
<div class="nx-recommendation-heading">{heading}{subject}</div>
<p class="nx-recommendation-title">{title}</p>
<ol class="nx-recommendation-steps">{steps}</ol>
</section>"""
_SUBJECT = '<span class="nx-recommendation-subject">{subject}</span>'


def render(verdicts: list[dict[str, Any]]) -> None:
    """Keep file-specific instructions visible in either assessment view.

    Recommendations are optional: a missing explanation must not manufacture an
    operational instruction from a prediction table whose meaning the UI cannot know.
    """
    for verdict in verdicts:
        recommendation = verdict.get("recommendation")
        if not recommendation:
            continue
        subject = verdict.get("subject")
        st.markdown(
            _CARD.format(
                heading=escape(RECOMMENDATION_HEADING),
                subject=_SUBJECT.format(subject=escape(str(subject))) if subject else "",
                title=escape(str(recommendation["title"])),
                steps="".join(
                    f"<li>{escape(str(step))}</li>" for step in recommendation["steps"]
                ),
            ),
            unsafe_allow_html=True,
        )
