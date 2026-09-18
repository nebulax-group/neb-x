"""Every dimension of the app: its identity, the words on screen, and the palette.

Paths live in ``src/common/config.py`` and subsystem schemas in ``src/<sub>/config.py``;
nothing here restates either. Nothing in ``src/app/`` should hold a literal that could
change — copy, colour and page identity all resolve to a name defined in this file.
"""

from src.common.config import SUBSYSTEMS

PAGE_TITLE = "Train Condition Monitoring"
PAGE_LAYOUT = "centered"
EYEBROW = "depot diagnostics"
STANDFIRST = "Add a system's sensor files. Read its condition, then download the result."

# The organisers' own folder names, so a judge reads the same word in the app, in the
# info kits and in the prediction filenames.
SUBSYSTEM_LABELS = {
    "door": "Door",
    "acv": "ACV",
    "rail": "Rail Corrugation",
    "shm": "SHM",
}

# What each system listens to, in the words of someone who maintains trains rather
# than someone who wrote the model. Presentation only: a fifth subsystem adds a line
# here, never a branch anywhere else.
SUBSYSTEM_BLURBS = {
    "door": "Motor current through every open and close cycle",
    "acv": "Cabin and ambient temperature across the cars",
    "rail": "Axle-box vibration and shock along the track",
    "shm": "Dynamic stress on the car body structure",
}

for _name, _mapping in (("SUBSYSTEM_LABELS", SUBSYSTEM_LABELS), ("SUBSYSTEM_BLURBS", SUBSYSTEM_BLURBS)):
    if set(_mapping) != set(SUBSYSTEMS):
        raise RuntimeError(
            f"{_name} covers {sorted(_mapping)}, expected {sorted(SUBSYSTEMS)}. "
            "The app offers exactly these keys, so a missing one disappears from the UI silently."
        )

READY_CHIP = "{ready} of {total} systems ready"

BOARD_HEADING = "Choose a system to check"
BOARD_STANDFIRST = "Pick the system your recordings came from."
BOARD_READY = "Model ready"
BOARD_IDLE = "No model yet"
BOARD_WAITING = "Pick a system to continue."
BOARD_SELECT = "Select"
BOARD_SELECTED = "Selected"

UPLOAD_PROMPT = "{label} recordings"
UPLOAD_HELP = "Several files at once is fine. Accepted: {formats}."
UPLOAD_WAITING = "Add at least one file to run {label}."
SPINNER_MESSAGE = "Running the {label} model..."
DOWNLOAD_LABEL = "Download predictions"
UNAVAILABLE_MESSAGE = "{label} has no trained model yet. Pick another system."
ERROR_HINT = "Check the files match the system selected, then try again."
RESULTS_HEADING = "Assessment"
READOUT_CAPTIONS = {
    "system_caption": "System",
    "rows_caption": "Rows returned",
    "output_caption": "Output file",
}

UPLOAD_DIR_PREFIX = "neb-x-uploads-"
SELECTED_STATE_KEY = "nx_selected_subsystem"
PANEL_STATE_KEY = "nx_panel_index"

STEP_COUNTER = "Step {current} of {total}"
STEP_BACK = "Back"
STEP_NEXT = "Next"
STEP_NUMBER = "{number:02d}"

# A depot condition desk seen at night: deep petrol rather than neutral black, so the
# ground reads as an instrument surface and not as a dark-mode switch. The accent is
# instrument cyan, and green/amber/red are kept back for signal aspects — they carry
# meaning a subsystem supplies, never a severity the app invented.
# Every foreground/background pair clears WCAG AA at 4.5:1; re-check with that
# threshold before changing any value here.
PALETTE = {
    "abyss": "#0A1319",
    "deck": "#101F27",
    "deck-high": "#172B35",
    "hairline": "#213A46",
    "hairline-strong": "#2E4E5C",
    "chalk": "#E9F1F4",
    "chalk-dim": "#93A9B4",
    "instrument": "#5BC8DE",
    "instrument-deep": "#2E97AE",
    "instrument-wash": "#123039",
    "clear": "#43B888",
    "caution": "#E3A93F",
    "danger": "#E4584C",
}

SANS_STACK = "'Archivo', 'Helvetica Neue', system-ui, sans-serif"
MONO_STACK = "'IBM Plex Mono', 'SF Mono', Menlo, monospace"
FONT_IMPORT_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Archivo:wght@400;500;600;700&"
    "family=IBM+Plex+Mono:wght@400;500;600&display=swap"
)

# Streamlit paints its own widgets from .streamlit/config.toml, which is TOML and cannot
# import this file. This mapping is what lets the app verify the two agree at startup
# instead of drifting into a stylesheet and a widget theme that disagree on screen.
THEME_CONFIG_COLOURS = {
    "primaryColor": "instrument",
    "backgroundColor": "abyss",
    "secondaryBackgroundColor": "deck",
    "textColor": "chalk",
    "linkColor": "instrument",
    "borderColor": "hairline",
    "dataframeBorderColor": "hairline",
    "dataframeHeaderBackgroundColor": "deck-high",
    "greenColor": "clear",
    "redColor": "danger",
    "orangeColor": "caution",
    "blueColor": "instrument",
    "blueBackgroundColor": "instrument-wash",
    "blueTextColor": "chalk",
}

EXPLAIN_HEADING = "How this reading was reached"
EXPLAIN_STANDFIRST = "The model's own workings, one step at a time."
EXPLAIN_FAILED = "Results are ready to download. The explanation could not be drawn ({reason})."

# Rows are sized rather than the chart, so a one-file and a sixteen-file batch keep
# identical bar thickness instead of stretching to fill a fixed height.
CHART_ROW_HEIGHT = 30
CHART_ROW_PADDING = 0.25
CHART_PADDING = 24
# The rotated y-axis title sits outside the plotting area, and at phone width the
# default padding is not enough to hold it and the tick labels; it clips at the edge.
CHART_PADDING_LEFT = 46
# Streamlit sets autosize.contains="padding", so a chart's declared height is the whole
# SVG: padding and the x-axis come out of it. Heights below are the plotting area wanted,
# and this is the room the axis labels plus title need on top of it.
CHART_AXIS_ALLOWANCE = 48
TRACE_PLOT_HEIGHT = 240
CHART_LABEL_OFFSET = 8
CHART_TITLE_FONT_SIZE = 12
CHART_LABEL_FONT_SIZE = 12
