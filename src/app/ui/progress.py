"""What a system looks like while it is working, and what keeps the page current.

The panel sits under the same head, and takes the same shape, as the verdict that
replaces it, so the answer lands where the reader is already looking. The view switch
still appears with the answer; reserving room for it would mean showing a control that
does nothing yet.

The watch is a fragment. It reruns on its own timer without re-executing the script,
and asks for a full rerun only when the queue has moved, so a page with nothing
outstanding is not polling at all. A system reaching the front of the queue counts as
the queue moving, or the board would go on calling it queued while it worked.

What it compares against is the standing the board **drew**, not the standing at the
end of the run. The worker usually starts between those two moments, and recording the
later one means the watch is already holding the change it exists to notice.
"""

from html import escape
from typing import MutableMapping

import streamlit as st

from src.app import jobs
from src.app.config import (
    CARD_QUEUED,
    CARD_RUNNING,
    POLL_SECONDS,
    QUEUED_DETAIL,
    QUEUED_HEADING,
    QUEUED_HEADLINE,
    RESULTS_HEADING,
    RUNNING_DETAIL,
    RUNNING_HEADING,
    RUNNING_HEADLINE,
)
from src.app.ui import section

_SEEN_KEY = "nx_jobs_seen"

# Left-aligned at column zero on purpose: st.markdown reads four leading spaces as
# an indented code block and would print this markup instead of rendering it.
_PANEL = """<div class="nx-running {tone}">
<div class="nx-verdict-flag"><span class="nx-lamp nx-lit {lamp}"></span>
<span class="nx-running-word">{heading}</span></div>
<p class="nx-verdict-headline">{headline}</p>
<p class="nx-verdict-detail">{detail}</p>
<div class="nx-progress" role="progressbar" aria-label="{heading}"></div>
</div>"""


def render_running(subsystem_label: str, working: bool = True) -> None:
    """Say where this system is in the queue, and that the page is usable meanwhile."""
    heading, headline, detail = (
        (RUNNING_HEADING, RUNNING_HEADLINE, RUNNING_DETAIL)
        if working
        else (QUEUED_HEADING, QUEUED_HEADLINE, QUEUED_DETAIL)
    )
    section.render(RESULTS_HEADING)
    st.markdown(
        _PANEL.format(
            tone="nx-tone-work",
            lamp="nx-pulse" if working else "",
            heading=escape(heading),
            headline=escape(headline.format(label=subsystem_label)),
            detail=escape(detail),
        ),
        unsafe_allow_html=True,
    )


@st.fragment(run_every=POLL_SECONDS)
def _tick() -> None:
    if jobs.pipeline(st.session_state) != st.session_state.get(_SEEN_KEY):
        st.rerun()


def watch(state: MutableMapping, standing: dict[str, str]) -> None:
    """Keep the page in step with a queue that moves after the script has returned."""
    state[_SEEN_KEY] = drawn = frozenset(
        (subsystem, place == CARD_RUNNING)
        for subsystem, place in standing.items()
        if place in (CARD_QUEUED, CARD_RUNNING)
    )
    if drawn:
        _tick()
