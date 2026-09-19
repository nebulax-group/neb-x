"""The result area, in its two modes: the answer, or everything behind it.

The two readers this page has to serve want opposite things. An operator wants a
decision and its urgency and nothing competing with it; an engineer meeting the
data for the first time wants to see how the reading was reached. Showing both at
once serves neither, so the modes are exclusive and the answer is the default.

Composition only. The verdict, the table and the panels are drawn by their own
files, and nothing here knows which subsystem produced any of them.
"""

from typing import Any

import pandas as pd
import streamlit as st

from src.app.config import (
    EXPLAIN_FAILED,
    RESULT_VIEW_STATE_KEY,
    RESULTS_HEADING,
    VIEW_LABELS,
    VIEW_NO_VERDICT,
    VIEW_ORDER,
    VIEW_PROMPT,
    VIEW_SIMPLE,
    VIEW_TECHNICAL,
)
from src.app.services import split_panels
from src.app.ui import explain, recommendation, results, section, verdict

_TOGGLE_KEY = "nx-view-toggle"
_BUTTON_KEY = "nx-view-{view}"


def _choose(view: str, state_key: str) -> None:
    st.session_state[state_key] = view


def _current_view(state_key: str) -> str:
    """The selected mode, defaulting to the answer."""
    view = st.session_state.get(state_key, VIEW_SIMPLE)
    return view if view in VIEW_LABELS else VIEW_SIMPLE


def _render_toggle(scope: str) -> str:
    state_key = f"{RESULT_VIEW_STATE_KEY}-{scope}"
    with st.container(key=_TOGGLE_KEY):
        # st.segmented_control arrived in a recent Streamlit, and the deployed host may
        # not offer the Python that pins it. The buttons are the same control drawn by
        # hand rather than a different affordance, so the page reads the same either way.
        if hasattr(st, "segmented_control"):
            chosen = st.segmented_control(
                VIEW_PROMPT,
                list(VIEW_ORDER),
                format_func=VIEW_LABELS.get,
                key=state_key,
                persist_state="session",
                default=VIEW_SIMPLE,
                # Without this a second click clears the selection, and the result
                # area would be showing a mode no control claims to be on.
                required=True,
            )
            return chosen if chosen in VIEW_LABELS else VIEW_SIMPLE

        current = _current_view(state_key)
        for column, view in zip(st.columns(len(VIEW_ORDER) + 2), VIEW_ORDER):
            with column:
                st.button(
                    VIEW_LABELS[view],
                    key=_BUTTON_KEY.format(view=view),
                    type="primary" if view == current else "secondary",
                    width="stretch",
                    on_click=_choose,
                    args=(view, state_key),
                )
        return current


def render(
    frame: pd.DataFrame,
    download_name: str,
    subsystem_label: str,
    panels: list[dict[str, Any]],
    explain_failure: str | None = None,
) -> None:
    """Draw the assessment: a mode switch, then whichever mode is selected."""
    section.render(RESULTS_HEADING)
    view = _render_toggle(subsystem_label)

    if explain_failure is not None:
        st.caption(EXPLAIN_FAILED.format(reason=explain_failure))

    verdicts, workings = split_panels(panels)

    if view == VIEW_TECHNICAL:
        recommendation.render(verdicts)
        results.render_readout(frame, subsystem_label)
        results.render_table(frame)
        explain.render(workings, scope=subsystem_label)
        return

    if verdicts:
        verdict.render(verdicts)
        recommendation.render(verdicts)
    else:
        st.caption(VIEW_NO_VERDICT.format(view=VIEW_LABELS[VIEW_TECHNICAL]))

    # The first of the workings, by the contract in services.py: a subsystem leads with
    # the panel that answers the question, so this is the one chart worth the space.
    if workings:
        explain.render_panel(workings[0])
