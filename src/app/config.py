"""Every dimension of the app: its identity, the words on screen, and the palette.

Paths live in ``src/common/config.py`` and subsystem schemas in ``src/<sub>/config.py``;
nothing here restates either. Nothing in ``src/app/`` should hold a literal that could
change — copy, colour and page identity all resolve to a name defined in this file.
"""

from src.common.config import SUBSYSTEMS

PAGE_TITLE = "Train Condition Monitoring"
PAGE_LAYOUT = "centered"
EYEBROW = "neb-x fleet diagnostics"
STANDFIRST = (
    "Choose the system you want checked, add the sensor files recorded from it, "
    "and the assessment appears below ready to download."
)

# The organisers' own folder names, so a judge reads the same word in the app, in the
# info kits and in the prediction filenames.
SUBSYSTEM_LABELS = {
    "door": "Door",
    "acv": "ACV",
    "rail": "Rail Corrugation",
    "shm": "SHM",
}

if set(SUBSYSTEM_LABELS) != set(SUBSYSTEMS):
    raise RuntimeError(
        f"SUBSYSTEM_LABELS covers {sorted(SUBSYSTEM_LABELS)}, expected {sorted(SUBSYSTEMS)}. "
        "The app offers exactly these keys, so a missing one disappears from the UI silently."
    )

SUBSYSTEM_PROMPT = "Which system are you checking?"
UPLOAD_PROMPT = "Upload your {label} data files"
UPLOAD_HELP = (
    "Drag the files here or browse for them. You can add several at once. "
    "Accepted formats: {formats}."
)
SPINNER_MESSAGE = "Reading your files and running the {label} model..."
DOWNLOAD_LABEL = "Download predictions (CSV)"
UNAVAILABLE_MESSAGE = (
    "{label} results are not available yet — there is no trained model for it. "
    "Choose another system above to run one now."
)
ERROR_HINT = (
    "Check that the files you uploaded are the ones for the system selected above, "
    "then try again."
)
READOUT_CAPTIONS = {
    "system_caption": "System",
    "rows_caption": "Rows returned",
    "output_caption": "Output file",
}

UPLOAD_DIR_PREFIX = "neb-x-uploads-"

# Warm paper rather than the cool blue-grey of a stock theme, and the oxide orange of
# weathered rail for the accent. Every foreground/background pair clears WCAG AA at 4.5:1;
# re-check with that threshold before changing any value here.
PALETTE = {
    "ink": "#14171A",
    "ink-muted": "#55595C",
    "paper": "#F3F1EC",
    "surface": "#FCFBF8",
    "rule": "#D6D1C7",
    "rule-strong": "#B9B2A4",
    "grid-header": "#EAE6DE",
    "oxide": "#A8481C",
    "oxide-deep": "#8A3A16",
    "oxide-wash": "#F4E7DF",
    "green": "#2E6A4A",
    "red": "#9E2B20",
    "amber": "#8A6208",
    "info": "#2F5560",
    "info-wash": "#E7ECEC",
    "info-ink": "#22414A",
}

SANS_STACK = "'IBM Plex Sans', 'Segoe UI', system-ui, sans-serif"
MONO_STACK = "'IBM Plex Mono', 'SF Mono', Menlo, monospace"
FONT_IMPORT_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=IBM+Plex+Mono:wght@400;500;600&"
    "family=IBM+Plex+Sans:wght@400;500;600;700&display=swap"
)

# Streamlit paints its own widgets from .streamlit/config.toml, which is TOML and cannot
# import this file. This mapping is what lets the app verify the two agree at startup
# instead of drifting into a stylesheet and a widget theme that disagree on screen.
THEME_CONFIG_COLOURS = {
    "primaryColor": "oxide",
    "backgroundColor": "paper",
    "secondaryBackgroundColor": "surface",
    "textColor": "ink",
    "linkColor": "oxide-deep",
    "borderColor": "rule",
    "dataframeBorderColor": "rule",
    "dataframeHeaderBackgroundColor": "grid-header",
    "greenColor": "green",
    "redColor": "red",
    "orangeColor": "amber",
    "blueColor": "info",
    "blueBackgroundColor": "info-wash",
    "blueTextColor": "info-ink",
}
