"""Every dimension of the Door subsystem. Nothing else restates one of these."""

# Column names exactly as they appear in Train.csv / Test.csv.
COLUMN_TIME = "Datetime"
COLUMN_CURRENT = "Motor current(mA)"
COLUMN_POSITION = "Door leaf position"
COLUMN_OPENING = "Door is opening"
COLUMN_CLOSING = "Door is closing"

# The controller only samples while a door moves, so cycle boundaries are silences.
# Inside a cycle rows are 20 ms apart; the shortest observed silence is 10.2 s.
CYCLE_GAP_SECONDS = 0.1

OPERATION_OPEN = "Open"
OPERATION_CLOSE = "Close"
OPERATIONS = (OPERATION_OPEN, OPERATION_CLOSE)

LABEL_NORMAL = "Normal"
LABEL_ABNORMAL = "Abnormal resistance"

ANSWER_COLUMN_STATUS = "status"
ANSWER_COLUMN_OPERATION = "operation"

EXPECTED_TRAIN_SEGMENTS = 110

# Mean current divided by the median for the same operation in the same file.
# Any value in 1.08-1.13 gives 0/110 training errors; 1.10 is the midpoint of that plateau.
RATIO_THRESHOLD = 1.10

# The severities this subsystem can report, as the app's panel protocol names them.
SEVERITY_CLEAR = "clear"
SEVERITY_CAUTION = "caution"
SEVERITY_DANGER = "danger"

# Consecutive flagged cycles before a stream is called sustained rather than occasional.
# The info kit's business case is that "prolonged exposure may lead to door jamming,
# motor overload, and running faults" (1.1), and the 110 labelled training cycles put a
# figure on prolonged: abnormal cycles arrive mostly alone, and the longest unbroken run
# in the whole stream is three. A run that long is therefore the worst the reference data
# shows, not a band invented here.
ABNORMAL_RUN_ALERT = 3

CV_SPLITS = 5
CV_REPEATS = 10
CV_RANDOM_STATE = 0

SUBMISSION_COLUMNS = ("start_time", "end_time", "prediction")

RECOMMENDATIONS = {
    SEVERITY_CLEAR: {
        "title": "Save this reading and monitor the next recording",
        "steps": (
            "Download the predictions to keep a record of this door's cycles.",
            "Compare a later recording for new resistance flags; follow the normal inspection schedule.",
        ),
    },
    SEVERITY_CAUTION: {
        "title": "Review the flagged cycles and arrange a door inspection",
        "steps": (
            "Select the flagged cycle blocks below to see their opening or closing move and exact times.",
            "Share these times with the maintenance team to check for obstruction or mechanical resistance using the door inspection procedure.",
            "After inspection, upload a fresh recording and check whether the flags recur.",
        ),
    },
    SEVERITY_DANGER: {
        "title": "Escalate repeated resistance to the maintenance team",
        "steps": (
            "Select the consecutive flagged cycles below and download their times for the maintenance team.",
            "Request a prompt door inspection and follow the depot's fault-handling procedure.",
            "After corrective work, upload a fresh recording to check for recurring resistance.",
        ),
    },
}
