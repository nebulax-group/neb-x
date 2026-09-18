"""The stylesheet that puts the palette on screen, and the check that it is the only one.

Colour, type and copy are defined in ``src/app/config.py``; this module turns the palette
into CSS custom properties and writes the rules that use them. Streamlit paints its own
widgets from ``.streamlit/config.toml``, so ``apply`` first checks that file agrees with
the palette — a stylesheet and a widget theme that disagree is the one failure here that
looks deliberate on screen and would survive to the demo video.
"""

import tomllib

import streamlit as st

from src.app.config import (
    FONT_IMPORT_URL,
    MONO_STACK,
    PALETTE,
    SANS_STACK,
    THEME_CONFIG_COLOURS,
)
from src.common.config import STREAMLIT_CONFIG_PATH

_TOKENS = ":root{" + "".join(f"--nx-{name}:{value};" for name, value in PALETTE.items()) + "}"

_STYLESHEET = """
html, body, .stApp, [data-testid="stAppViewContainer"] {
    font-family: %(sans)s;
    color: var(--nx-ink);
}

[data-testid="stHeader"] { background: transparent; }

/* The stock toolbar and the rainbow loading bar are the two things that read as
   "a Streamlit app" rather than as this tool; the demo video is graded on that. */
[data-testid="stToolbar"], [data-testid="stDecoration"] { display: none; }

.block-container {
    max-width: 1080px;
    padding-top: 2.75rem;
    padding-bottom: 4rem;
}

/* Widget labels read as instrument legends rather than sentences, which keeps
   the eye on the values instead of the chrome. */
[data-testid="stWidgetLabel"] p {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--nx-ink-muted);
}

[data-testid="stFileUploaderDropzone"] {
    background: var(--nx-surface);
    border: 1px dashed var(--nx-rule-strong);
    border-radius: 2px;
}

[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--nx-oxide); }

/* The results grid is painted to a canvas, so it takes its face from the `font`
   key in .streamlit/config.toml — CSS cannot reach inside it. */

.stDownloadButton button, .stButton button {
    font-weight: 600;
    letter-spacing: 0.02em;
    border-radius: 2px;
    transition: background-color 180ms ease-out, border-color 180ms ease-out;
}

.nx-masthead {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    padding-bottom: 0.9rem;
    border-bottom: 2px solid var(--nx-ink);
}

.nx-mark { flex: none; }

.nx-masthead-text { display: flex; flex-direction: column; gap: 0.25rem; }

.nx-eyebrow {
    font-family: %(mono)s;
    font-size: 0.68rem;
    font-weight: 500;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--nx-oxide);
}

.stApp h1.nx-title {
    margin: 0;
    padding: 0;
    font-size: 1.6rem;
    font-weight: 600;
    line-height: 1.15;
    letter-spacing: -0.015em;
}

.stApp p.nx-standfirst {
    margin: 1rem 0 2rem;
    max-width: 62ch;
    color: var(--nx-ink-muted);
    line-height: 1.6;
}

.nx-readout {
    display: flex;
    flex-wrap: wrap;
    gap: 2.5rem;
    margin: 1.5rem 0 1rem;
    padding: 0.9rem 1.1rem;
    background: var(--nx-surface);
    border: 1px solid var(--nx-rule);
    border-left: 3px solid var(--nx-oxide);
    border-radius: 2px;
}

.nx-readout dt {
    font-size: 0.66rem;
    font-weight: 600;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    color: var(--nx-ink-muted);
}

.nx-readout dd {
    margin: 0.2rem 0 0;
    font-family: %(mono)s;
    font-size: 1.05rem;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    color: var(--nx-ink);
}

/* Streamlit ships rules for h1-h3 and p that beat a bare class selector, so every
   heading and paragraph below is qualified by element and scoped to .stApp. Dropping
   the qualifier silently hands the type scale back to Streamlit's defaults. */
.nx-explain-head {
    margin: 3.25rem 0 0;
    padding-top: 1.6rem;
    border-top: 2px solid var(--nx-ink);
}

.stApp h2.nx-explain-title {
    margin: 0;
    padding: 0;
    font-size: 1.15rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--nx-ink);
}

.stApp p.nx-explain-standfirst {
    margin: 0.45rem 0 0;
    max-width: 62ch;
    color: var(--nx-ink-muted);
    line-height: 1.6;
}

.nx-panel-head {
    margin: 2.25rem 0 0.35rem;
    padding-top: 1.1rem;
    border-top: 1px solid var(--nx-rule);
}

.nx-panel-titles {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.6rem;
}

.stApp h3.nx-panel-title {
    margin: 0;
    padding: 0;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--nx-ink);
}

/* The filename is the one string on the page the user supplied, so it is set in
   mono and boxed: it reads as a value being reported back, not as our own prose. */
.nx-panel-subject {
    padding: 0.12rem 0.4rem;
    font-family: %(mono)s;
    font-size: 0.72rem;
    font-weight: 500;
    color: var(--nx-oxide-deep);
    background: var(--nx-oxide-wash);
    border-radius: 2px;
}

.stApp p.nx-panel-caption {
    margin: 0.5rem 0 0;
    max-width: 68ch;
    font-size: 0.88rem;
    line-height: 1.6;
    color: var(--nx-ink-muted);
}

.stApp p.nx-panel-key {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    margin: -0.5rem 0 0;
    font-size: 0.78rem;
    color: var(--nx-ink-muted);
}

.nx-key-mark {
    display: inline-block;
    width: 2px;
    height: 0.85rem;
    background: var(--nx-ink);
}

.nx-metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 1px;
    margin: 1.1rem 0 0;
    background: var(--nx-rule);
    border: 1px solid var(--nx-rule);
    border-radius: 2px;
    overflow: hidden;
}

.nx-metric {
    padding: 0.95rem 1.05rem;
    background: var(--nx-surface);
}

.nx-metric dt {
    font-size: 0.66rem;
    font-weight: 600;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    color: var(--nx-ink-muted);
}

.nx-metric dd {
    margin: 0.35rem 0 0;
    font-family: %(mono)s;
    font-size: 1.5rem;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    line-height: 1.1;
    color: var(--nx-ink);
}

/* Inside the <dd> rather than beside it: a <div> in a <dl> may only hold <dt> and
   <dd>, so the detail has to live within the value it describes. */
.nx-metric dd span {
    display: block;
    margin-top: 0.35rem;
    font-family: %(sans)s;
    font-size: 0.78rem;
    font-weight: 400;
    line-height: 1.45;
    color: var(--nx-ink-muted);
}

@media (prefers-reduced-motion: reduce) {
    .stDownloadButton button, .stButton button { transition: none; }
}
""" % {"sans": SANS_STACK, "mono": MONO_STACK}


def verify_widget_theme() -> None:
    """Fail if .streamlit/config.toml has drifted from the palette."""
    if not STREAMLIT_CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"No widget theme at {STREAMLIT_CONFIG_PATH}; Streamlit would paint its own "
            "colours over this stylesheet."
        )

    configured = tomllib.loads(STREAMLIT_CONFIG_PATH.read_text()).get("theme", {})
    drifted = {
        key: (configured.get(key), PALETTE[token])
        for key, token in THEME_CONFIG_COLOURS.items()
        if str(configured.get(key, "")).upper() != PALETTE[token].upper()
    }
    if drifted:
        detail = ", ".join(
            f"{key}={found!r} but palette says {expected}" for key, (found, expected) in drifted.items()
        )
        raise ValueError(f"{STREAMLIT_CONFIG_PATH} disagrees with the palette: {detail}.")


def apply() -> None:
    """Install the stylesheet. Call once, before anything else renders."""
    verify_widget_theme()
    st.markdown(
        f"<style>@import url('{FONT_IMPORT_URL}');{_TOKENS}{_STYLESHEET}</style>",
        unsafe_allow_html=True,
    )
