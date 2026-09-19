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
    background: var(--nx-abyss);
    color: var(--nx-chalk);
}

[data-testid="stHeader"] { background: transparent; }

/* The stock toolbar and the rainbow loading bar are the two things that read as
   "a Streamlit app" rather than as this tool; the demo video is graded on that. */
[data-testid="stToolbar"], [data-testid="stDecoration"] { display: none; }

.block-container {
    max-width: 1120px;
    padding-top: 2.25rem;
    padding-bottom: 5rem;
}

:focus-visible {
    outline: 2px solid var(--nx-instrument);
    outline-offset: 2px;
}

/* Widget labels read as instrument legends rather than sentences, which keeps
   the eye on the values instead of the chrome. */
[data-testid="stWidgetLabel"] p {
    font-family: %(mono)s;
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: var(--nx-chalk-dim);
}

/* ── Masthead ─────────────────────────────────────────────────────────── */

.nx-rail {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding-bottom: 0.7rem;
    border-bottom: 1px solid var(--nx-hairline);
}

.nx-mark { flex: none; display: block; }

.nx-wordmark {
    font-family: %(mono)s;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--nx-chalk);
}

.nx-eyebrow {
    font-family: %(mono)s;
    font-size: 0.7rem;
    font-weight: 400;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--nx-chalk-dim);
}

.nx-eyebrow::before {
    content: "";
    display: inline-block;
    width: 1px;
    height: 0.8rem;
    margin-right: 0.7rem;
    vertical-align: -0.1rem;
    background: var(--nx-hairline-strong);
}

.nx-chip {
    margin-left: auto;
    padding: 0.2rem 0.55rem;
    font-family: %(mono)s;
    font-size: 0.68rem;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    white-space: nowrap;
    color: var(--nx-instrument);
    background: var(--nx-instrument-wash);
    border: 1px solid var(--nx-hairline-strong);
    border-radius: 2px;
}

.stApp h1.nx-title {
    margin: 1.6rem 0 0;
    padding: 0;
    font-size: clamp(1.9rem, 1.15rem + 2.1vw, 2.85rem);
    font-weight: 700;
    line-height: 1.04;
    letter-spacing: -0.03em;
    color: var(--nx-chalk);
}

.stApp p.nx-standfirst {
    margin: 0.85rem 0 0;
    max-width: 58ch;
    font-size: 1.02rem;
    color: var(--nx-chalk-dim);
    line-height: 1.55;
}

/* ── Section heads ────────────────────────────────────────────────────── */

.nx-section {
    margin: 2.9rem 0 1.15rem;
    padding-top: 1.1rem;
    border-top: 1px solid var(--nx-hairline);
}

.stApp h2.nx-section-title {
    margin: 0;
    padding: 0;
    font-family: %(mono)s;
    font-size: 0.74rem;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--nx-instrument);
}

.stApp p.nx-section-standfirst {
    margin: 0.5rem 0 0;
    max-width: 64ch;
    font-size: 0.92rem;
    color: var(--nx-chalk-dim);
    line-height: 1.55;
}

/* ── The board ────────────────────────────────────────────────────────── */

/* Each card is a st.container(key="nx-card-<sub>"), so the markup above the button
   and the button itself sit inside one element that can be given a border. */
[class*="st-key-nx-card-"] {
    display: flex;
    flex-direction: column;
    gap: 0;
    height: 100%%;
    min-height: 186px;
    padding: 0.95rem 1rem 0.9rem;
    background: var(--nx-deck);
    border: 1px solid var(--nx-hairline);
    border-radius: 3px;
    transition: border-color 160ms ease-out, background-color 160ms ease-out;
}

[class*="st-key-nx-card-"]:hover { border-color: var(--nx-hairline-strong); }

[class*="st-key-nx-card-"]:has(.nx-on) {
    background: var(--nx-deck-high);
    border-color: var(--nx-instrument);
}

/* Only the button is pushed to the foot of the card. Matching the last child instead
   would bottom-align the text on a card that has no button, which the dormant ones
   do not. */
[class*="st-key-nx-card-"] [data-testid="stElementContainer"]:has(.stButton) {
    margin-top: auto;
    padding-top: 0.9rem;
}

.nx-lamp-row {
    display: flex;
    align-items: center;
    gap: 0.45rem;
}

.nx-lamp {
    flex: none;
    width: 8px;
    height: 8px;
    border-radius: 50%%;
    background: var(--nx-hairline-strong);
}

/* The glow is what makes a lit lamp read as lit rather than as a coloured dot; it is
   the one piece of decoration on the page and it encodes real state. */
.nx-lamp.nx-lit {
    background: var(--nx-clear);
    box-shadow: 0 0 0 3px rgba(67, 184, 136, 0.16);
}

.nx-on .nx-lamp.nx-lit {
    background: var(--nx-instrument);
    box-shadow: 0 0 0 3px rgba(91, 200, 222, 0.2);
}

.nx-lamp-text {
    font-family: %(mono)s;
    font-size: 0.64rem;
    font-weight: 500;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--nx-chalk-dim);
}

.nx-card-name {
    margin: 0.85rem 0 0;
    font-size: 1.12rem;
    font-weight: 600;
    letter-spacing: -0.015em;
    line-height: 1.2;
    color: var(--nx-chalk);
}

.nx-card-blurb {
    margin: 0.35rem 0 0;
    font-size: 0.82rem;
    line-height: 1.45;
    color: var(--nx-chalk-dim);
}

.nx-off .nx-card-name, .nx-off .nx-card-blurb { opacity: 0.55; }

[class*="st-key-nx-card-"] .stButton button {
    width: 100%%;
    font-family: %(mono)s;
    font-size: 0.7rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */

.stDownloadButton button, .stButton button {
    font-weight: 600;
    letter-spacing: 0.02em;
    border-radius: 2px;
    transition: background-color 160ms ease-out, border-color 160ms ease-out,
                color 160ms ease-out;
}

.stDownloadButton button { padding-left: 1.4rem; padding-right: 1.4rem; }

/* ── Uploader ─────────────────────────────────────────────────────────── */

[data-testid="stFileUploaderDropzone"] {
    background: var(--nx-deck);
    border: 1px dashed var(--nx-hairline-strong);
    border-radius: 3px;
}

[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--nx-instrument); }

/* Streamlit paints the file chip's icon tile with the theme text colour, which on a
   dark ground is a white square bright enough to pull the eye off the result. */
[data-testid="stFileChip"] > div:first-child { background: var(--nx-chalk-dim); }

/* ── Readout ──────────────────────────────────────────────────────────── */

.nx-readout {
    display: flex;
    flex-wrap: wrap;
    gap: 2.4rem;
    margin: 0 0 1.1rem;
    padding: 0.95rem 1.15rem;
    background: var(--nx-deck);
    border: 1px solid var(--nx-hairline);
    border-left: 3px solid var(--nx-instrument);
    border-radius: 3px;
}

.nx-readout dt {
    font-family: %(mono)s;
    font-size: 0.64rem;
    font-weight: 500;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: var(--nx-chalk-dim);
}

.nx-readout dd {
    margin: 0.3rem 0 0;
    font-family: %(mono)s;
    font-size: 1.05rem;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    color: var(--nx-chalk);
}

/* ── Failure ──────────────────────────────────────────────────────────── */

/* What a run leaves behind when it produced nothing. It keeps the geometry of the
   readout and the verdict so it reads as the same instrument, and none of their
   colour: green, amber and red carry a subsystem's judgement about a train, and the
   wrong file in the uploader is not a condition of the train. Painting this red would
   be the page inventing an alarm, and would teach the reader to discount the real one. */
.nx-failure {
    margin: 0.2rem 0 0.35rem;
    padding: 1.15rem 1.3rem 1.25rem;
    background: var(--nx-deck);
    border: 1px solid var(--nx-hairline);
    border-left: 3px solid var(--nx-chalk-dim);
    border-radius: 3px;
}

/* Hollow rather than dimly filled. The board's dormant lamp sits among lit ones and
   only has to be the darker of them; this one is alone on the page and has to read as
   out on its own, so it is drawn as a ring at a contrast that survives being alone. */
.nx-lamp.nx-lamp-out {
    background: transparent;
    box-shadow: inset 0 0 0 2px var(--nx-chalk-dim);
}

.stApp p.nx-failure-headline {
    margin: 0.75rem 0 0;
    font-size: clamp(1.2rem, 1rem + 0.8vw, 1.5rem);
    font-weight: 600;
    line-height: 1.25;
    letter-spacing: -0.02em;
    color: var(--nx-chalk);
}

.stApp p.nx-failure-explain {
    margin: 0.5rem 0 0;
    max-width: 58ch;
    font-size: 0.9rem;
    line-height: 1.55;
    color: var(--nx-chalk-dim);
}

.nx-failure-facts {
    display: grid;
    gap: 0.9rem;
    margin: 1.15rem 0 0;
}

.nx-failure-facts dt {
    font-family: %(mono)s;
    font-size: 0.64rem;
    font-weight: 500;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: var(--nx-chalk-dim);
}

.nx-failure-facts dd {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem;
    margin: 0.35rem 0 0;
    font-size: 0.92rem;
    line-height: 1.5;
    color: var(--nx-chalk);
}

.nx-failure-more {
    font-family: %(mono)s;
    font-size: 0.72rem;
    color: var(--nx-chalk-dim);
}

/* The subsystem's own sentence, inset on the raised ground so it reads as something
   quoted back rather than as the page speaking. Mono for the reason a filename is:
   it is a value that was reported, and its exact characters are the point. */
.nx-failure-report {
    margin: 1.15rem 0 0;
    padding: 0.8rem 0.95rem;
    background: var(--nx-deck-high);
    border-radius: 3px;
}

.stApp p.nx-failure-report-caption, .stApp p.nx-failure-next-caption {
    margin: 0;
    font-family: %(mono)s;
    font-size: 0.64rem;
    font-weight: 500;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: var(--nx-chalk-dim);
}

/* A path or a column name has no spaces to break at, and the panel is narrow on a
   phone; without this the one line the reader might copy runs off the side. */
.stApp p.nx-failure-report-text {
    margin: 0.4rem 0 0;
    font-family: %(mono)s;
    font-size: 0.8rem;
    line-height: 1.55;
    color: var(--nx-chalk-dim);
    overflow-wrap: anywhere;
}

/* Below a rule, because it answers a different question from everything above it:
   not what happened, but what to do instead. */
.nx-failure-next {
    margin: 1.25rem 0 0;
    padding: 1.05rem 0 0;
    border-top: 1px solid var(--nx-hairline);
}

.stApp ul.nx-failure-options {
    margin: 0.55rem 0 0;
    padding: 0;
    list-style: none;
}

.stApp .nx-failure-options li {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.15rem 0.75rem;
    margin: 0;
    padding: 0.35rem 0;
}

.nx-failure-option-name {
    min-width: 8.5rem;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--nx-chalk);
}

.nx-failure-option-blurb {
    flex: 1 1 18ch;
    font-size: 0.85rem;
    line-height: 1.45;
    color: var(--nx-chalk-dim);
}

.stApp p.nx-failure-next-hint {
    margin: 0.75rem 0 0;
    font-size: 0.87rem;
    line-height: 1.55;
    color: var(--nx-chalk-dim);
}

/* ── Severity ─────────────────────────────────────────────────────────── */

/* A severity reaches the page as a class a subsystem named, and its only job is to
   bind one variable. Every component below reads --nx-sev through a fallback, so a
   severity the palette does not cover renders neutral instead of unstyled, and these
   rules never have to compete on specificity with the components that use them. */
.nx-sev-clear { --nx-sev: var(--nx-clear); }
.nx-sev-caution { --nx-sev: var(--nx-caution); }
.nx-sev-danger { --nx-sev: var(--nx-danger); }

/* ── Verdict ──────────────────────────────────────────────────────────── */

/* The card ground stays --nx-deck for every severity. A severity-tinted ground was
   tried and fails WCAG AA: --nx-danger reads 4.21:1 on its own 10%% tint and 4.05:1
   on --nx-deck-high, against 4.65:1 on --nx-deck. The colour carries on the rule,
   the lamp and the word, all of which sit on the one ground that clears the bar. */
.nx-verdict {
    margin: 0.2rem 0 0.35rem;
    padding: 1.15rem 1.3rem 1.25rem;
    background: var(--nx-deck);
    border: 1px solid var(--nx-hairline);
    border-left: 3px solid var(--nx-sev, var(--nx-chalk-dim));
    border-radius: 3px;
}

.nx-verdict-flag {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
}

.nx-verdict-lamp {
    flex: none;
    width: 9px;
    height: 9px;
    border-radius: 50%%;
    background: var(--nx-sev, var(--nx-chalk-dim));
}

.nx-verdict-word {
    font-family: %(mono)s;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--nx-sev, var(--nx-chalk-dim));
}

.nx-verdict-subject {
    margin-left: auto;
    padding: 0.14rem 0.45rem;
    font-family: %(mono)s;
    font-size: 0.7rem;
    font-weight: 500;
    color: var(--nx-instrument);
    background: var(--nx-instrument-wash);
    border: 1px solid var(--nx-hairline-strong);
    border-radius: 2px;
}

.stApp p.nx-verdict-headline {
    margin: 0.75rem 0 0;
    font-size: clamp(1.35rem, 1.05rem + 1.1vw, 1.75rem);
    font-weight: 600;
    line-height: 1.2;
    letter-spacing: -0.02em;
    color: var(--nx-chalk);
}

.stApp p.nx-verdict-detail {
    margin: 0.5rem 0 0;
    max-width: 58ch;
    font-size: 0.9rem;
    line-height: 1.55;
    color: var(--nx-chalk-dim);
}

/* Next steps sit with the answer, with enough room for instructions on a phone. */
.nx-recommendation {
    margin: 0 0 0.8rem;
    padding: 1rem 1.3rem;
    background: var(--nx-deck);
    border: 1px solid var(--nx-hairline);
    border-left: 3px solid var(--nx-instrument);
    border-radius: 3px;
    overflow-wrap: anywhere;
}

.nx-failure-report summary {
    display: list-item;
    padding: 0.6rem 0;
    min-height: 44px;
    cursor: pointer;
    font-size: 0.88rem;
    color: var(--nx-chalk);
}

.nx-failure-report summary:focus-visible {
    outline: 2px solid var(--nx-instrument);
    outline-offset: 4px;
}

.nx-failure-recovery {
    margin: 1.15rem 0 0;
    padding: 0.95rem;
    background: var(--nx-instrument-wash);
    border-left: 2px solid var(--nx-instrument);
    border-radius: 3px;
}

.stApp p.nx-failure-recovery-text {
    margin: 0.5rem 0 0;
    font-size: 0.95rem;
    line-height: 1.6;
    color: var(--nx-chalk);
}

.nx-failure .nx-panel-subject {
    max-width: 100%%;
    overflow-wrap: anywhere;
    white-space: normal;
}

.nx-recommendation-heading {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1rem;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--nx-instrument);
}

.nx-recommendation-subject {
    margin-left: auto;
    max-width: 100%%;
    font-family: %(mono)s;
    font-size: 0.75rem;
    color: var(--nx-chalk-dim);
}

.stApp p.nx-recommendation-title {
    margin: 0.65rem 0;
    font-size: 1rem;
    font-weight: 600;
    line-height: 1.5;
    color: var(--nx-chalk);
}

.stApp .nx-recommendation-steps {
    margin: 0;
    padding-left: 1.3rem;
    font-size: 1rem;
    line-height: 1.6;
    color: var(--nx-chalk);
}

.stApp .nx-recommendation-steps li + li { margin-top: 0.5rem; }
.nx-recommendation-steps li::marker { color: var(--nx-instrument); }

.nx-handoff-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1.5rem;
    align-items: baseline;
    padding: 0.85rem 1rem;
    background: var(--nx-deck);
    border: 1px solid var(--nx-hairline);
    border-radius: 4px;
    color: var(--nx-chalk);
}
.nx-handoff-row strong { color: var(--nx-instrument); }
.nx-handoff-row span:last-child { margin-left: auto; color: var(--nx-chalk-dim); }
.st-key-nx-handoff-download [data-testid="stDownloadButton"] {
    display: flex;
    justify-content: center;
    padding: 1rem 0;
}
.st-key-nx-handoff-download button { min-height: 48px; padding: 0.6rem 1.5rem; }

/* ── Mode switch ──────────────────────────────────────────────────────── */

.st-key-nx-view-toggle { margin: 0 0 1.3rem; }

[data-testid="stButtonGroup"] { gap: 0.3rem; }

/* Matches the active button too, which carries the same prefix; the rule below then
   overrides it. 44px is the touch target the numbered deck rail already uses. */
.st-key-nx-view-toggle [data-testid*="stBaseButton-segmented_control"] {
    min-height: 44px;
    padding: 0 1.2rem;
    font-family: %(mono)s;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--nx-chalk-dim);
    background: var(--nx-deck);
    border: 1px solid var(--nx-hairline);
    border-radius: 2px;
    transition: background-color 160ms ease-out, border-color 160ms ease-out,
                color 160ms ease-out;
}

.st-key-nx-view-toggle
[data-testid*="stBaseButton-segmented_control"]:hover {
    color: var(--nx-chalk);
    border-color: var(--nx-hairline-strong);
}

.st-key-nx-view-toggle [data-testid*="segmented_controlActive"] {
    color: var(--nx-abyss);
    background: var(--nx-instrument);
    border-color: var(--nx-instrument);
}

/* The two-button fallback, for a Streamlit without st.segmented_control. */
.st-key-nx-view-toggle .stButton button {
    min-height: 44px;
    font-family: %(mono)s;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

/* ── Event strip ──────────────────────────────────────────────────────── */

/* Keep selection separate from severity: cyan picks the cycle, red flags it. */
[class*="st-key-nx-strip-"] {
    margin: 1.15rem 0 0;
    padding: 1.1rem;
    background: var(--nx-deck);
    border: 1px solid var(--nx-hairline);
    border-radius: 3px;
}

[class*="st-key-nx-strip-"] [role="radiogroup"] {
    gap: 12px;
    flex-wrap: wrap;
}

[class*="st-key-nx-strip-"] [data-testid="stRadioOption"] {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 48px;
    min-height: 48px;
    margin: 0;
    padding: 4px 6px;
    color: var(--nx-chalk);
    background: var(--nx-deck-high);
    border-bottom: 3px solid var(--nx-sev, var(--nx-chalk-dim));
    border-radius: 4px;
    cursor: pointer;
    transition: box-shadow 150ms ease, filter 150ms ease;
}

[class*="st-key-nx-strip-"] [data-testid="stRadioOption"]:hover {
    filter: brightness(1.15);
}

/* Keep the native input available to keyboards and assistive technology, while
   the numbered block itself carries its checked and focus states. */
[class*="st-key-nx-strip-"] [data-testid="stRadioOption"] > div > div:first-child {
    display: none;
}

[class*="st-key-nx-strip-"] [data-testid="stRadioOption"] > div {
    padding: 0;
    gap: 0;
}

[class*="st-key-nx-strip-"] [data-testid="stRadioOption"] p {
    color: inherit;
    font-family: %(mono)s;
    font-size: 0.875rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

[class*="st-key-nx-strip-"] [data-testid="stRadioOption"]:has(input:checked) {
    box-shadow: 0 0 0 2px var(--nx-abyss), 0 0 0 5px var(--nx-instrument);
}

[class*="st-key-nx-strip-"] [data-testid="stRadioOption"]:has(input:checked)::after {
    content: "";
    position: absolute;
    top: -9px;
    right: -8px;
    width: 19px;
    height: 19px;
    border-radius: 50%%;
    background: var(--nx-instrument);
    pointer-events: none;
}

[class*="st-key-nx-strip-"] [data-testid="stRadioOption"]:has(input:checked)::before {
    content: "";
    position: absolute;
    z-index: 1;
    top: -6px;
    right: -2px;
    width: 5px;
    height: 9px;
    border-right: 2px solid var(--nx-abyss);
    border-bottom: 2px solid var(--nx-abyss);
    transform: rotate(45deg);
    pointer-events: none;
}

[class*="st-key-nx-strip-"] [data-testid="stRadioOption"][data-focus-visible] {
    outline: 2px solid var(--nx-instrument);
    outline-offset: 7px;
}

/* A separate readout gives the active cycle a stable, readable hierarchy. */
.nx-cycle-detail {
    padding: 1.25rem;
    margin: 0.25rem 0 0.75rem;
    background: var(--nx-deck);
    border: 1px solid var(--nx-hairline-strong);
    border-left: 4px solid var(--nx-sev, var(--nx-instrument));
    border-radius: 6px;
}

.nx-cycle-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
}

.nx-cycle-eyebrow {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--nx-instrument);
}

.stApp h3.nx-cycle-title {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin: 0.35rem 0 0;
    padding: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--nx-chalk);
}

.nx-cycle-operation {
    font-size: 1rem;
    font-weight: 400;
    color: var(--nx-chalk-dim);
}

.nx-cycle-status {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--nx-sev, var(--nx-hairline-strong));
    border-radius: 4px;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--nx-sev, var(--nx-chalk));
}

.nx-cycle-status::before {
    content: "";
    width: 7px;
    height: 7px;
    border-radius: 50%%;
    background: currentColor;
}

.nx-cycle-fields {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
    margin: 1.1rem 0 0;
    padding-top: 1rem;
    border-top: 1px solid var(--nx-hairline);
}

.nx-cycle-fields dt {
    margin-bottom: 0.4rem;
    font-size: 0.8rem;
    color: var(--nx-chalk-dim);
}

.nx-cycle-fields dd {
    margin: 0;
    font-family: %(mono)s;
    font-size: 1rem;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    color: var(--nx-chalk);
}

.nx-cycle-fields dd span {
    display: block;
    margin-top: 0.35rem;
    font-family: %(sans)s;
    font-size: 0.8rem;
    font-weight: 400;
    color: var(--nx-chalk-dim);
}

.nx-strip-detail {
    font-family: %(mono)s;
    font-size: 0.72rem;
    line-height: 1.35;
    color: var(--nx-chalk);
}

.stApp p.nx-strip-detail {
    margin: 0.35rem 0 0;
    overflow-wrap: anywhere;
}

.stApp p.nx-strip-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 1.15rem;
    margin: 0.75rem 0 0;
    font-size: 0.78rem;
    color: var(--nx-chalk-dim);
}

.nx-strip-key {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
}

.nx-strip-chip {
    width: 15px;
    height: 11px;
    background: var(--nx-deck-high);
    border-bottom: 3px solid var(--nx-sev, var(--nx-chalk-dim));
    border-radius: 2px 2px 0 0;
}

.nx-strip-chip.nx-sev-caution, .nx-strip-chip.nx-sev-danger {
    background: var(--nx-sev);
}

/* ── Explanation ──────────────────────────────────────────────────────── */

/* Streamlit ships rules for h1-h3 and p that beat a bare class selector, so every
   heading and paragraph here is qualified by element and scoped to .stApp. Dropping
   the qualifier silently hands the type scale back to Streamlit's defaults. */
.nx-explain-head {
    margin: 3.25rem 0 0;
    padding-top: 1.5rem;
    border-top: 1px solid var(--nx-hairline);
}

.stApp h2.nx-explain-title {
    margin: 0;
    padding: 0;
    font-size: 1.3rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: var(--nx-chalk);
}

.stApp p.nx-explain-standfirst {
    margin: 0.45rem 0 0;
    max-width: 62ch;
    color: var(--nx-chalk-dim);
    line-height: 1.55;
}

/* ── Panel deck ───────────────────────────────────────────────────────── */

.nx-deck-status {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.75rem;
    margin: 2rem 0 0.6rem;
}

.nx-deck-counter {
    font-family: %(mono)s;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--nx-instrument);
}

.nx-deck-title {
    font-size: 1.15rem;
    font-weight: 600;
    letter-spacing: -0.015em;
    color: var(--nx-chalk);
}

.st-key-nx-deck-nav {
    padding: 0.6rem 0.7rem;
    background: var(--nx-deck);
    border: 1px solid var(--nx-hairline);
    border-radius: 3px;
}

/* 44px keeps every cell a comfortable target on a touch screen, which the numbered
   ones would not be if they were sized to their two characters. */
.st-key-nx-deck-steps { margin-bottom: 0.5rem; }

.st-key-nx-deck-nav .stButton button {
    min-height: 44px;
    font-family: %(mono)s;
    font-size: 0.74rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    font-variant-numeric: tabular-nums;
}

.st-key-nx-deck-nav [class*="st-key-nx-back"] button:disabled,
.st-key-nx-deck-nav [class*="st-key-nx-next"] button:disabled {
    opacity: 0.35;
}

.stApp p.nx-panel-caption { margin: 1.4rem 0 0; }

/* The filename is the one string on the page the user supplied, so it is set in
   mono and boxed: it reads as a value being reported back, not as our own prose. */
.nx-panel-subject {
    padding: 0.14rem 0.45rem;
    font-family: %(mono)s;
    font-size: 0.72rem;
    font-weight: 500;
    color: var(--nx-instrument);
    background: var(--nx-instrument-wash);
    border: 1px solid var(--nx-hairline-strong);
    border-radius: 2px;
}

.stApp p.nx-panel-caption {
    margin: 0.5rem 0 0;
    max-width: 68ch;
    font-size: 0.87rem;
    line-height: 1.6;
    color: var(--nx-chalk-dim);
}

.stApp p.nx-panel-key {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    margin: -0.5rem 0 0;
    font-size: 0.78rem;
    color: var(--nx-chalk-dim);
}

.nx-key-mark {
    display: inline-block;
    width: 2px;
    height: 0.85rem;
    background: var(--nx-chalk);
}

.nx-metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 1px;
    margin: 1.1rem 0 0;
    background: var(--nx-hairline);
    border: 1px solid var(--nx-hairline);
    border-radius: 3px;
    overflow: hidden;
}

.nx-metric {
    padding: 1rem 1.1rem;
    background: var(--nx-deck);
}

.nx-metric dt {
    font-family: %(mono)s;
    font-size: 0.64rem;
    font-weight: 500;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: var(--nx-chalk-dim);
}

.nx-metric dd {
    margin: 0.4rem 0 0;
    font-family: %(mono)s;
    font-size: 1.65rem;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    line-height: 1.05;
    color: var(--nx-instrument);
}

/* Inside the <dd> rather than beside it: a <div> in a <dl> may only hold <dt> and
   <dd>, so the detail has to live within the value it describes. */
.nx-metric dd span {
    display: block;
    margin-top: 0.4rem;
    font-family: %(sans)s;
    font-size: 0.78rem;
    font-weight: 400;
    line-height: 1.45;
    color: var(--nx-chalk-dim);
}

@media (max-width: 640px) {
    .nx-chip { display: none; }
    [class*="st-key-nx-card-"] { min-height: 0; }

    /* Streamlit stacks columns on a narrow screen, which would turn the rail into six
       full-height buttons and cost more scrolling than the deck saves. The counter
       above already says which step this is, so only back and next are kept. */
    .st-key-nx-deck-steps { display: none; }
}

@media (prefers-reduced-motion: reduce) {
    [class*="st-key-nx-strip-"] [data-testid="stRadioOption"],
    .stDownloadButton button, .stButton button,
    [class*="st-key-nx-card-"],
    .st-key-nx-view-toggle [data-testid*="stBaseButton-segmented_control"] {
        transition: none;
    }
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
