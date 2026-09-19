"""The panel shown in place of a result when a run cannot finish.

Rendering only. Which category a failure belongs to, and the sentence behind it, are
decided in ``src/app/services.py``; the words are in ``src/app/config.py``. Nothing
here knows anything about a subsystem beyond the key it was handed, so the panel can
say which systems are ready without ever claiming to know which one these files
belong to. That guess is the one thing an error screen must not make: it would be
wrong exactly when the reader is least able to tell.
"""

from html import escape

import streamlit as st

from src.app.config import (
    FAILURE_EXPECTS_CAPTION,
    FAILURE_DIAGNOSTICS,
    FAILURE_EXPLANATIONS,
    FAILURE_FILES_CAPTION,
    FAILURE_FILES_MORE,
    FAILURE_FILES_SHOWN,
    FAILURE_HEADLINES,
    FAILURE_MISMATCH,
    FAILURE_NEXT_CAPTION,
    FAILURE_NEXT_HINT,
    FAILURE_NEXT_NONE,
    FAILURE_REPORT_CAPTION,
    FAILURE_RECOVERY,
    FAILURE_RECOVERY_CAPTION,
    FAILURE_STATUS,
    FAILURE_UNAVAILABLE,
    SUBSYSTEM_BLURBS,
    SUBSYSTEM_LABELS,
    UPLOAD_REQUIREMENTS,
)
from src.app.services import Failure
from src.common.config import SUPPORTED_DATA_EXTENSIONS

# Left-aligned at column zero on purpose: st.markdown reads four leading spaces as
# an indented code block and would print this markup instead of rendering it.
_PANEL = """<section class="nx-failure" role="alert">
<div class="nx-lamp-row"><span class="nx-lamp nx-lamp-out" aria-hidden="true"></span>
<span class="nx-lamp-text">{status}</span></div>
<p class="nx-failure-headline">{headline}</p>
<p class="nx-failure-explain">{explanation}</p>
{facts}{recovery}{report}{options}
</section>"""

_FACTS = """<dl class="nx-failure-facts">
{rows}
</dl>"""
_FACT = """<div><dt>{caption}</dt><dd>{value}</dd></div>"""
_CHIP = """<span class="nx-panel-subject">{name}</span>"""
_MORE = """<span class="nx-failure-more">{more}</span>"""

_REPORT = """<details class="nx-failure-report">
<summary>{summary}</summary>
<p class="nx-failure-report-caption">{caption}</p>
<p class="nx-failure-report-text">{reason}</p>
</details>"""

_RECOVERY = """<div class="nx-failure-recovery">
<p class="nx-failure-next-caption">{caption}</p>
<p class="nx-failure-recovery-text">{instruction}</p>
</div>"""

_OPTIONS = """<div class="nx-failure-next">
<p class="nx-failure-next-caption">{caption}</p>
<ul class="nx-failure-options">
{items}
</ul>
<p class="nx-failure-next-hint">{hint}</p>
</div>"""
_OPTION = """<li><span class="nx-failure-option-name">{label}</span>\
<span class="nx-failure-option-blurb">{blurb}</span></li>"""
_NO_OPTIONS = """<div class="nx-failure-next">
<p class="nx-failure-next-hint">{hint}</p>
</div>"""


def _elsewhere(subsystem: str, available: dict[str, bool]) -> tuple[str, ...]:
    """The systems worth turning to now: ready, and not the one that just failed."""
    return tuple(key for key, ready in available.items() if ready and key != subsystem)


def _chips(subjects: tuple[str, ...]) -> str:
    shown = "".join(_CHIP.format(name=escape(name)) for name in subjects[:FAILURE_FILES_SHOWN])
    hidden = len(subjects) - FAILURE_FILES_SHOWN
    if hidden <= 0:
        return shown
    return shown + _MORE.format(more=escape(FAILURE_FILES_MORE.format(count=hidden)))


def _facts(diagnosis: Failure, label: str, subsystem: str) -> str:
    rows = []
    # Only where it answers the question the reader is actually asking. "What Door
    # reads" tells someone holding the wrong file what the right one looks like; on a
    # file that never opened, or a system with nothing trained, it is a distraction.
    if diagnosis.kind == FAILURE_MISMATCH:
        rows.append(
            _FACT.format(
                caption=escape(FAILURE_EXPECTS_CAPTION.format(label=label)),
                value=escape(UPLOAD_REQUIREMENTS[subsystem]),
            )
        )
    if diagnosis.subjects:
        rows.append(
            _FACT.format(
                caption=escape(FAILURE_FILES_CAPTION),
                value=_chips(diagnosis.subjects),
            )
        )
    return _FACTS.format(rows="\n".join(rows)) if rows else ""


def _report(diagnosis: Failure, label: str) -> str:
    """The system's own sentence, kept as evidence rather than as the message.

    It is the line worth quoting to whoever maintains the model, so it is shown and
    not swallowed; it is also the line a first-day reader cannot act on, so it sits
    below the plain-words account rather than in place of one.
    """
    if not diagnosis.reason:
        return ""
    return _REPORT.format(
        summary=escape(FAILURE_DIAGNOSTICS),
        caption=escape(FAILURE_REPORT_CAPTION.format(label=label)),
        reason=escape(diagnosis.reason),
    )


def _options(subsystem: str, available: dict[str, bool]) -> str:
    elsewhere = _elsewhere(subsystem, available)
    if not elsewhere:
        return _NO_OPTIONS.format(hint=escape(FAILURE_NEXT_NONE))
    return _OPTIONS.format(
        caption=escape(FAILURE_NEXT_CAPTION),
        items="\n".join(
            _OPTION.format(
                label=escape(SUBSYSTEM_LABELS[key]),
                blurb=escape(SUBSYSTEM_BLURBS[key]),
            )
            for key in elsewhere
        ),
        hint=escape(FAILURE_NEXT_HINT),
    )


def render(diagnosis: Failure, subsystem: str, available: dict[str, bool]) -> None:
    """Draw the failure: what happened, which files, and which systems are ready."""
    label = SUBSYSTEM_LABELS[subsystem]
    st.markdown(
        _PANEL.format(
            status=escape(FAILURE_STATUS[diagnosis.kind]),
            headline=escape(FAILURE_HEADLINES[diagnosis.kind].format(label=label)),
            explanation=escape(
                FAILURE_EXPLANATIONS[diagnosis.kind].format(
                    label=label, formats=", ".join(SUPPORTED_DATA_EXTENSIONS)
                )
            ),
            facts=_facts(diagnosis, label, subsystem),
            recovery=_RECOVERY.format(
                caption=escape(FAILURE_RECOVERY_CAPTION),
                instruction=escape(FAILURE_RECOVERY[diagnosis.kind]),
            ),
            report=_report(diagnosis, label),
            options=_options(subsystem, available) if diagnosis.kind == FAILURE_MISMATCH else "",
        ),
        unsafe_allow_html=True,
    )


def render_unavailable(subsystem: str, available: dict[str, bool]) -> None:
    """Draw the one failure that happens before any file is read."""
    render(Failure(FAILURE_UNAVAILABLE, "", ()), subsystem, available)
