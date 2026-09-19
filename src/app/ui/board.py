"""The board of monitored systems: one card per subsystem, and which one is selected.

Rendering only, and deliberately generic — the board is built by looping over the
labels it is handed, so a fifth subsystem appears here without this file changing.
Whether a subsystem can run is decided in ``src/app/services.py`` and where it stands
in ``src/app/workspace.py``; this file only draws the answer.

The card is a ``st.container`` with a key, which Streamlit turns into a stable
``st-key-nx-card-<subsystem>`` class. That is what lets the description and the
button underneath it sit inside one bordered card rather than two stacked blocks.
"""

from html import escape

import streamlit as st

from src.app.config import (
    BOARD_SELECT,
    BOARD_SELECTED,
    CARD_LAMPS,
    CARD_TONES,
    CARD_WORDS,
)

_CARD_KEY = "nx-card-{subsystem}"
_BUTTON_KEY = "nx-pick-{subsystem}"

# Left-aligned at column zero on purpose: st.markdown reads four leading spaces as
# an indented code block and would print this markup instead of rendering it.
_CARD = """<div class="nx-card {state}">
<div class="nx-lamp-row"><span class="nx-lamp {lamp}"></span>{status}</div>
<div class="nx-card-name">{label}</div>
<div class="nx-card-blurb">{blurb}</div>
</div>"""

_STATUS = '<span class="nx-lamp-text">{status}</span>'


def _choose(state_key: str, subsystem: str) -> None:
    # A callback rather than a return value: Streamlit runs it before the rerun, so
    # the card draws already selected. Reading the click afterwards would leave the
    # highlight one interaction behind what the rest of the page is showing.
    st.session_state[state_key] = subsystem


def render(
    labels: dict[str, str],
    blurbs: dict[str, str],
    available: dict[str, bool],
    standing: dict[str, str],
    state_key: str,
) -> str | None:
    """Draw every system as a card and return the selected key, if there is one."""
    selected = st.session_state.get(state_key)

    for column, (subsystem, label) in zip(st.columns(len(labels)), labels.items()):
        ready = available[subsystem]
        place = standing[subsystem]
        chosen = subsystem == selected
        word = CARD_WORDS[place]
        state = " ".join(
            name
            for name, on in (
                ("nx-on", chosen),
                ("nx-off", not ready),
                (CARD_TONES[place], True),
            )
            if on and name
        )
        with column, st.container(key=_CARD_KEY.format(subsystem=subsystem)):
            st.markdown(
                _CARD.format(
                    state=state,
                    lamp=f"nx-lit {CARD_LAMPS[place]}".strip() if ready else "",
                    status=_STATUS.format(status=escape(word)) if word else "",
                    label=escape(label),
                    blurb=escape(blurbs[subsystem]),
                ),
                unsafe_allow_html=True,
            )
            if ready:
                st.button(
                    BOARD_SELECTED if chosen else BOARD_SELECT,
                    key=_BUTTON_KEY.format(subsystem=subsystem),
                    disabled=chosen,
                    type="primary" if chosen else "secondary",
                    width="stretch",
                    on_click=_choose,
                    args=(state_key, subsystem),
                )

    return selected
