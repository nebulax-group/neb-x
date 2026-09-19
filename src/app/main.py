"""The app's entry point and routing: pick a system, add files, predict, download.

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

from src.app import cache, config, services  # noqa: E402
from src.app.ui import assessment, board, failure, masthead, section, theme, upload  # noqa: E402


def main() -> None:
    st.set_page_config(page_title=config.PAGE_TITLE, layout=config.PAGE_LAYOUT)
    theme.apply()

    available = {key: services.is_available(key) for key in config.SUBSYSTEM_LABELS}
    masthead.render(
        config.EYEBROW,
        config.PAGE_TITLE,
        config.STANDFIRST,
        chip=config.READY_CHIP.format(
            ready=sum(available.values()), total=len(available)
        ),
    )

    section.render(config.BOARD_HEADING, config.BOARD_STANDFIRST)
    subsystem = board.render(
        config.SUBSYSTEM_LABELS,
        config.SUBSYSTEM_BLURBS,
        available,
        config.SELECTED_STATE_KEY,
    )
    if subsystem is None:
        st.caption(config.BOARD_WAITING)
        return

    label = config.SUBSYSTEM_LABELS[subsystem]
    # The board disables a system with no model, so this only fires if one goes
    # missing between reruns — still said out loud rather than crashed on.
    if not available[subsystem]:
        failure.render_unavailable(subsystem, available)
        return

    uploads = upload.render_uploader(label, subsystem)
    if not uploads:
        upload.render_waiting(label)
        return

    try:
        with st.spinner(config.SPINNER_MESSAGE.format(label=label)):
            answer = cache.reading(subsystem, uploads)
    except Exception as exc:  # a non-technical user needs a way out, not a traceback
        failure.render(services.describe_failure(exc, uploads), subsystem, available)
        return

    assessment.render(
        answer.frame,
        services.prediction_filename(subsystem),
        label,
        answer.panels,
        answer.explain_failure,
    )


if __name__ == "__main__":
    main()
