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

# The severities this subsystem can report, as the app's panel protocol names them.
# There is deliberately no clear: the task is to rank, not to decide whether anything
# is wrong, and acv_case_05 settles it - the known-faulty car there sits 0.71 degrees
# BELOW its own setpoint and leads the second car by 0.018, so a cool, flat file is
# not evidence of health. Reporting one as clear would invent an all-clear the data
# cannot support.
SEVERITY_CAUTION = "caution"
SEVERITY_DANGER = "danger"

# How far the top car must lead the second before the ranking is called well separated.
# Measured leads across the five usable reference cases, every one of which the ranking
# gets right: 0.018, 0.103, 0.449, 0.472 and 1.136. Anything in 0.17-0.44 splits them
# the same way; 0.25 is the middle of that empty band.
CLEAR_LEAD_DEGREES = 0.25

RANKED_CARS_SEPARATOR = "|"
SUBMISSION_COLUMNS = ("file_id", "ranked_cars")

RECOMMENDATION_FIRST = "Start the ACV inspection with Car {car}"
RECOMMENDATION_CLOSE = "Check Car {car} and Car {second} together"
RECOMMENDATION_STEPS = (
    "Review the cabin temperature and cooling target for {cars} while cooling is active.",
    "Ask the maintenance team to confirm the cause using the ACV inspection procedure before treating the ranking as a refrigerant leak.",
    "After inspection or corrective work, upload a new recording and compare the car ranking.",
)
