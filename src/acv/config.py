"""Every dimension of the ACV subsystem."""

import re

# Per-car columns are 'Car <NN> - <parameter>'. 'Car model' must not match.
CAR_COLUMN_PATTERN = re.compile(r"^Car (\d{2}) - (.+)$")

# Parameter names are not stable across case files, so each signal has aliases.
INDOOR_TEMPERATURE_CANDIDATES = (
    "Indoor Average Temperature",
    "Passenger Cabin Temperature Detected Value",
)
COOLING_SETPOINT_CANDIDATES = (
    "ACV Control Temperature (Cooling)",
    "Target Temperature Value",
)
RUNNING_MODE_CANDIDATES = ("ACV Running Mode",)

# Modes in which the unit is actively cooling, for the duty-cycle signal.
COOLING_MODES = ("Automatic Cooling", "Full Cooling")

LABEL_FILENAME_COLUMN = "filename"
LABEL_CAR_COLUMN = "faulty_car"

# A different schema entirely - 483 columns, 59 parameters per car, only cars 01-04,
# and refrigeration pressures the test file does not have. It cannot validate a method
# aimed at the test schema.
EXCLUDED_FROM_VALIDATION = ("acv_case_04.xlsx",)

RANKED_CARS_SEPARATOR = "|"
SUBMISSION_COLUMNS = ("file_id", "ranked_cars")
