"""The app's entry point and routing: pick a subsystem, upload, predict, download.

Run from the repository root with ``streamlit run src/app/main.py``. Screens live
in ``src/app/ui/`` and the subsystem calls in ``src/app/services.py``; this file
holds neither, and never branches on which subsystem was chosen.
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

from src.app import config, services  # noqa: E402
from src.app.ui import explain, masthead, results, theme, upload  # noqa: E402


def main() -> None:
    st.set_page_config(page_title=config.PAGE_TITLE, layout=config.PAGE_LAYOUT)
    theme.apply()
    masthead.render(config.EYEBROW, config.PAGE_TITLE, config.STANDFIRST)

    subsystem = upload.render_subsystem_picker(config.SUBSYSTEM_LABELS)
    label = config.SUBSYSTEM_LABELS[subsystem]

    if not services.is_available(subsystem):
        results.render_unavailable(label)
        return

    uploads = upload.render_uploader(label)
    if not uploads:
        return

    try:
        staged = services.stage_uploads(uploads)
        with st.spinner(config.SPINNER_MESSAGE.format(label=label)):
            frame = services.run_prediction(subsystem, staged)
    except Exception as exc:  # a non-technical user needs a sentence, not a traceback
        results.render_error(str(exc))
        return

    results.render_results(frame, services.prediction_filename(subsystem), label)

    # Caught separately, and after the results are on screen: the prediction is the
    # compulsory deliverable, and losing it because an optional chart failed would be
    # the wrong trade. The failure is still stated rather than swallowed.
    try:
        with st.spinner(config.SPINNER_MESSAGE.format(label=label)):
            panels = services.explain_prediction(subsystem, staged)
    except Exception as exc:
        st.caption(config.EXPLAIN_FAILED.format(reason=exc))
        return

    explain.render(panels)


if __name__ == "__main__":
    main()
