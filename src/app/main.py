"""Route persistent subsystem windows and a shared maintenance review package.

Run from the repository root with ``streamlit run src/app/main.py``. Screens live
in ``src/app/ui/``, the subsystem calls in ``src/app/services.py`` and the promise
that each one runs once in ``src/app/cache.py``; this file holds none of the three,
and never branches on which subsystem was chosen.
"""

import sys
from pathlib import Path

import streamlit as st

# streamlit sets sys.path[0] to this script's own folder, so ``src.*`` does not
# resolve until the repository root is on the path. scripts/check_env.py does
# the same for the same reason.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.app import config, services, workspace  # noqa: E402
from src.app.ui import (  # noqa: E402
    assessment,
    board,
    failure,
    handoff,
    masthead,
    progress,
    section,
    theme,
    upload,
)


def main() -> None:
    st.set_page_config(page_title=config.PAGE_TITLE, layout=config.PAGE_LAYOUT)
    theme.apply()

    available = {key: services.is_available(key) for key in config.SUBSYSTEM_LABELS}
    # Every finished assessment, not only the selected system's: the handoff below
    # covers the whole session, so it cannot wait for each one to be looked at again.
    workspace.collect(st.session_state)
    # Before anything is drawn, so the board and the uploader both show this pass
    # where the selected system actually stands rather than where it stood last.
    outcome = advance(st.session_state.get(config.SELECTED_STATE_KEY), available)
    standing = workspace.standing(available, st.session_state)
    locked = {key: place in workspace.ON_QUEUE for key, place in standing.items()}

    masthead.render(config.EYEBROW, config.PAGE_TITLE, config.STANDFIRST)

    section.render(config.BOARD_HEADING, config.BOARD_STANDFIRST)
    subsystem = board.render(
        config.SUBSYSTEM_LABELS,
        config.SUBSYSTEM_BLURBS,
        available,
        standing,
        config.SELECTED_STATE_KEY,
    )
    upload.render_windows(subsystem, available, locked, workspace.reset)
    try:
        render_selected(subsystem, available, outcome)
    finally:
        handoff.render(workspace.runs(st.session_state))
        progress.watch(st.session_state, standing)


def advance(subsystem: str | None, available: dict[str, bool]) -> workspace.Outcome:
    """Start or collect the selected system's reading."""
    if subsystem is None or not available.get(subsystem):
        return workspace.Outcome(workspace.IDLE)
    return workspace.assess(subsystem, upload.files(subsystem), st.session_state)


def render_selected(subsystem, available, outcome: workspace.Outcome) -> None:
    if subsystem is None:
        st.caption(config.BOARD_WAITING)
        return

    label = config.SUBSYSTEM_LABELS[subsystem]
    # The board disables a system with no model, so this only fires if one goes
    # missing between reruns — still said out loud rather than crashed on.
    if not available[subsystem]:
        failure.render_unavailable(subsystem, available)
        return

    if outcome.state in workspace.ON_QUEUE:
        progress.render_running(label, working=outcome.state == workspace.RUNNING)
        return

    if outcome.state == workspace.FAILED:
        # A non-technical user needs a way out, not a traceback.
        described = services.describe_failure(outcome.error, upload.files(subsystem))
        failure.render(described, subsystem, available)
        return

    if outcome.state == workspace.IDLE:
        upload.render_waiting(label)
        return

    answer = outcome.run.reading
    assessment.render(
        answer.frame,
        services.prediction_filename(subsystem),
        label,
        answer.panels,
        answer.explain_failure,
    )


if __name__ == "__main__":
    main()
