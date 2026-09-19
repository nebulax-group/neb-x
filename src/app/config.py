"""Every dimension of the app: its identity, the words on screen, and the palette.

Paths live in ``src/common/config.py`` and subsystem schemas in ``src/<sub>/config.py``;
nothing here restates either. Nothing in ``src/app/`` should hold a literal that could
change — copy, colour and page identity all resolve to a name defined in this file.
"""

from src.common.config import SUBSYSTEM_LABELS, SUBSYSTEMS

PAGE_TITLE = "Train Condition Monitoring"
PAGE_LAYOUT = "centered"
EYEBROW = "depot diagnostics"
STANDFIRST = "Assess your recordings, review the findings, then prepare one maintenance handoff."

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

BOARD_HEADING = "Choose a system to check"
BOARD_STANDFIRST = "Pick the system your recordings came from."
BOARD_WAITING = "Pick a system to continue."
BOARD_SELECT = "Select"
BOARD_SELECTED = "Selected"

# Where a system stands, which is a fact about the queue and never about what a model
# found. Blue is nothing assessed yet, red is on the queue, green is an assessment
# that finished. A system with no model keeps the resting hairline and says so.
CARD_ABSENT = "absent"
CARD_IDLE = "idle"
CARD_QUEUED = "queued"
CARD_RUNNING = "running"
CARD_DONE = "done"
CARD_FAILED = "failed"
CARD_STANDINGS = (CARD_ABSENT, CARD_IDLE, CARD_QUEUED, CARD_RUNNING, CARD_DONE, CARD_FAILED)

# Silence is the resting state. A word appears beside the lamp only where the colour
# alone would not tell a reader what to do or wait for.
CARD_WORDS = {
    CARD_ABSENT: "No model yet",
    CARD_IDLE: "",
    CARD_QUEUED: "Queued",
    CARD_RUNNING: "Running",
    CARD_DONE: "",
    CARD_FAILED: "Not assessed",
}
CARD_TONES = {
    CARD_ABSENT: "",
    CARD_IDLE: "nx-tone-idle",
    CARD_QUEUED: "nx-tone-work",
    CARD_RUNNING: "nx-tone-work",
    CARD_DONE: "nx-tone-done",
    CARD_FAILED: "nx-tone-idle",
}
# Only the system whose turn it is moves. A queued one shares its colour and waits.
CARD_LAMPS = {
    CARD_ABSENT: "",
    CARD_IDLE: "",
    CARD_QUEUED: "",
    CARD_RUNNING: "nx-pulse",
    CARD_DONE: "",
    CARD_FAILED: "",
}

for _name, _mapping in (("CARD_WORDS", CARD_WORDS), ("CARD_TONES", CARD_TONES), ("CARD_LAMPS", CARD_LAMPS)):
    if set(_mapping) != set(CARD_STANDINGS):
        raise RuntimeError(
            f"{_name} covers {sorted(_mapping)}, expected {sorted(CARD_STANDINGS)}. "
            "A standing with no entry draws a card with no colour and no word."
        )

UPLOAD_PROMPT = "{label} recordings"
UPLOAD_HELP = "Accepted: {formats}. Keep the original filenames."
UPLOAD_REQUIREMENTS = {
    "door": "Upload exactly one continuous Door recording, with a header row containing Datetime, Motor current(mA), Door is opening and Door is closing.",
    "acv": "Upload one or more ACV case files with Car NN - … columns for cabin temperature and cooling setpoint. Use recordings, not the labels file.",
    "shm": "Upload one or more stress histories: one numeric column, no header, and at least two samples per file. Use recordings, not Train_Labels.csv.",
    "rail": "Upload one or more axle-box recordings: 129 columns starting with Rotating speed, then vibration and shock for each of the 64 axle boxes, one second at 10,000 samples per file.",
}
UPLOAD_WAITING = "Add at least one file to run {label}."
UPLOAD_LOCKED = "Files are locked until {label} finishes."
# A batch is assessed whole, so the only edit offered is replacing all of it. The
# per-file remove and add controls are hidden rather than left to imply otherwise.
UPLOAD_CLEAR = "Clear all"
UPLOAD_CLEAR_HELP = "Remove every file for this system and start again."
UPLOAD_BATCH = "Recordings are assessed as one batch. Clear all to swap them."
RESULTS_HEADING = "Assessment"

RUNNING_HEADING = "Running"
RUNNING_HEADLINE = "{label} is assessing your recordings."
RUNNING_DETAIL = "Switch to another system while this finishes. Its files are locked until it does."

QUEUED_HEADING = "Queued"
QUEUED_HEADLINE = "{label} is waiting its turn."
QUEUED_DETAIL = "Systems are assessed one at a time, in the order you started them."

REPORT_UNAVAILABLE = "Review evidence could not be prepared. Open the assessment and ask the app maintainer to review it."
RECOMMENDATION_HEADING = "What to do next"
READOUT_CAPTIONS = {
    "system_caption": "System",
    "rows_caption": "Rows returned",
}

HANDOFF_COPY = {
    "heading": "Maintenance handoff",
    "intro": "Collect the findings from your current review into one folder to share.",
    "session": "Latest assessment per system · Kept while this browser session is active. Switching systems keeps your files and results.",
    "empty": "Assess a recording to prepare a review package.",
    "count": "{count} review items",
    "incomplete": "Evidence incomplete",
    "maintainer": "App maintainer review needed",
    "warning": "{label}: review evidence is incomplete. The package will state this; it will not report an all-clear.",
    "missing": "Not assessed / unavailable: ",
    "metadata": "Add a reference or handoff note (optional)",
    "reference": "Review / work-order reference",
    "preparer": "Prepared by",
    "notes": "Asset, location and handoff notes",
    "notes_help": "Identify which source file belongs to which asset or measurement point. Include the intended recipient if known.",
    "contents": "ZIP includes a readable report, recommended actions, selected findings and bar charts. No raw recordings, full prediction tables or model binaries. Suggested recipients are maintenance roles; you choose who receives it.",
    "download": "Download review package",
    "open": "Extract the ZIP and open Report.html for charts, or Summary.txt for the text version. Nothing is sent automatically.",
}

# Failure copy distinguishes upload layout, unreadable files, missing setup, and
# processing errors. A model or app failure must not blame the user's recordings.
FAILURE_MISMATCH = "mismatch"
FAILURE_UNREADABLE = "unreadable"
FAILURE_UNAVAILABLE = "unavailable"
FAILURE_INTERNAL = "internal"
FAILURE_KINDS = (FAILURE_MISMATCH, FAILURE_UNREADABLE, FAILURE_UNAVAILABLE, FAILURE_INTERNAL)

FAILURE_STATUS = {
    FAILURE_MISMATCH: "Check your upload",
    FAILURE_UNREADABLE: "File could not be read",
    FAILURE_UNAVAILABLE: "Model unavailable",
    FAILURE_INTERNAL: "Assessment interrupted",
}
FAILURE_HEADLINES = {
    FAILURE_MISMATCH: "These files do not match {label}.",
    FAILURE_UNREADABLE: "We could not open this recording.",
    FAILURE_UNAVAILABLE: "{label} is not ready to run.",
    FAILURE_INTERNAL: "{label} could not finish the assessment.",
}
FAILURE_EXPLANATIONS = {
    FAILURE_MISMATCH: "Check the recording layout below. A supported file extension alone does not mean it contains the measurements {label} needs.",
    FAILURE_UNREADABLE: "A file is empty, damaged, or cannot be read as {formats}. No assessment was produced.",
    FAILURE_UNAVAILABLE: "The predictor, a required dependency, or its trained model is missing. This is an app setup issue.",
    FAILURE_INTERNAL: "The app encountered a processing problem. This does not establish that your recordings are incorrect.",
}
FAILURE_RECOVERY = {
    FAILURE_MISMATCH: "Remove the incorrect file using the × beside its name above, then browse for a matching recording. If these recordings belong to another system, select that system on the board and upload them there.",
    FAILURE_UNREADABLE: "Remove the unreadable file above. Export it again from the original source as CSV or XLSX, then upload the new copy. Changing the extension does not convert a file.",
    FAILURE_UNAVAILABLE: "Ask the app maintainer to restore the model or required dependencies, then retry your upload.",
    FAILURE_INTERNAL: "Remove and re-add the recording to retry. If the problem continues, share the diagnostic details below with the app maintainer.",
}
FAILURE_RECOVERY_CAPTION = "What to do next"
FAILURE_DIAGNOSTICS = "Diagnostic details"

for _name, _mapping in (
    ("FAILURE_STATUS", FAILURE_STATUS),
    ("FAILURE_HEADLINES", FAILURE_HEADLINES),
    ("FAILURE_EXPLANATIONS", FAILURE_EXPLANATIONS),
    ("FAILURE_RECOVERY", FAILURE_RECOVERY),
):
    if set(_mapping) != set(FAILURE_KINDS):
        raise RuntimeError(
            f"{_name} covers {sorted(_mapping)}, expected {sorted(FAILURE_KINDS)}. "
            "A failure kind with no copy for it renders as a panel with a blank line."
        )

# Describe the selected system's expected layout without guessing the uploaded
# file's origin from its name.
FAILURE_EXPECTS_CAPTION = "What {label} reads"
FAILURE_FILES_CAPTION = "Files added"
FAILURE_REPORT_CAPTION = "What {label} reported"
FAILURE_NEXT_CAPTION = "Other available systems"
FAILURE_NEXT_HINT = "Choose one on the board above, then add its files."
FAILURE_NEXT_NONE = "No other system has a model right now."
# Enough of a batch to recognise it by, short of listing sixteen SHM segments.
FAILURE_FILES_SHOWN = 6
FAILURE_FILES_MORE = "and {count} more"

UPLOAD_DIR_PREFIX = "neb-x-uploads-"

# Readings held at once. A reading keeps the whole recording it was drawn from, and
# the deployed host has about a gigabyte of memory, so this is a ceiling rather than
# a hit rate: coming back to the file before last is worth keeping, a whole session
# of them is not.
CACHE_MAX_READINGS = 4

# One worker, so the queue is the order systems were started in and two models never
# compete for the machine.
QUEUE_WORKERS = 1
# How often the page asks whether the queue has moved. Short enough to feel immediate,
# long enough that a wait is not a stream of reruns.
POLL_SECONDS = 0.4

SELECTED_STATE_KEY = "nx_selected_subsystem"
# A Streamlit uploader cannot be emptied by writing to its own state, so clearing one
# means drawing a new widget. The count is what makes its key different.
UPLOAD_GENERATION_KEY = "nx_upload_generation"
PANEL_STATE_KEY = "nx_panel_index"
RESULT_VIEW_STATE_KEY = "nx_result_view"

VIEW_SIMPLE = "simple"
VIEW_TECHNICAL = "technical"
VIEW_ORDER = (VIEW_SIMPLE, VIEW_TECHNICAL)
VIEW_LABELS = {VIEW_SIMPLE: "Answer", VIEW_TECHNICAL: "Details"}
VIEW_PROMPT = "Show"
VIEW_NO_VERDICT = "This system does not summarise itself yet. Open {view} for the full result."

STRIP_PICK_LABEL = "Select a cycle"
STRIP_PICK_HELP = "Click or tap a numbered cycle. Use the arrow keys to move between cycles."
STRIP_SELECTED_LABEL = "Selected cycle"

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

# A verdict names its severity as one of the palette keys above. The word beside it is
# what keeps the reading off colour alone, which a colour-blind operator and a greyscale
# recording of the demo both depend on.
SEVERITY_WORDS = {
    "clear": "Clear",
    "caution": "Caution",
    "danger": "Alert",
}

if not set(SEVERITY_WORDS) <= set(PALETTE):
    raise RuntimeError(
        f"SEVERITY_WORDS names {sorted(set(SEVERITY_WORDS) - set(PALETTE))}, which the "
        "palette cannot paint. A severity the app has no colour for renders unmarked."
    )

# The severity nothing is wrong at. An event strip opens on the first cell above it,
# because a reader arrives from a verdict that has just counted those cells and wants
# to know where the first one falls.
SEVERITY_RESTING = "clear"

if SEVERITY_RESTING not in SEVERITY_WORDS:
    raise RuntimeError(
        f"SEVERITY_RESTING is {SEVERITY_RESTING!r}, which is not one of "
        f"{sorted(SEVERITY_WORDS)}. Every cell would then count as raised."
    )

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
EXPLAIN_FAILED = "Assessment results are available in Details. The explanation could not be drawn ({reason})."

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
