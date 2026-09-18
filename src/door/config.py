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

CV_SPLITS = 5
CV_REPEATS = 10
CV_RANDOM_STATE = 0

SUBMISSION_COLUMNS = ("start_time", "end_time", "prediction")
