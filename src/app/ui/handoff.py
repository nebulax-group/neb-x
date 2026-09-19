"""One review-package action for the current session, visible below every window."""

from html import escape

import streamlit as st

from src.app import handoff as package
from src.app.config import HANDOFF_COPY as COPY, SUBSYSTEM_LABELS
from src.app.ui import section


def render(runs: dict) -> None:
    section.render(COPY["heading"], COPY["intro"])
    st.caption(COPY["session"])
    if not runs:
        st.info(COPY["empty"])
        return
    for key in SUBSYSTEM_LABELS:
        if key not in runs:
            continue
        run = runs[key]
        report = run.report
        count = len(report["findings"]) if report else None
        status = COPY["count"].format(count=count) if count is not None else COPY["incomplete"]
        recipient = report["recipient"] if report else COPY["maintainer"]
        st.markdown(
            f'<div class="nx-handoff-row"><strong>{escape(SUBSYSTEM_LABELS[key])}</strong><span>{status}</span><span>{escape(recipient)}</span></div>',
            unsafe_allow_html=True,
        )
        if report:
            st.caption(report["summary"])
        else:
            st.warning(COPY["warning"].format(label=SUBSYSTEM_LABELS[key]))
    missing = [label for key, label in SUBSYSTEM_LABELS.items() if key not in runs]
    if missing:
        st.caption(COPY["missing"] + ", ".join(missing))
    with st.expander(COPY["metadata"]):
        reference = st.text_input(COPY["reference"], key="nx-review-reference", max_chars=160)
        prepared_by = st.text_input(COPY["preparer"], key="nx-review-preparer", max_chars=120)
        notes = st.text_area(COPY["notes"], key="nx-review-notes", max_chars=2000, help=COPY["notes_help"])
    st.caption(COPY["contents"])
    filename, payload = package.build(runs, reference, prepared_by, notes)
    with st.container(key="nx-handoff-download", horizontal=True, horizontal_alignment="center"):
        st.download_button(COPY["download"], payload, file_name=filename, mime="application/zip", type="primary", on_click="ignore", key="nx-review-download", width="content")
    st.caption(COPY["open"])
