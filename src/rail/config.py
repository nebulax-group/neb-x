"""Every dimension of the rail subsystem: schema, geometry, spectra, model settings.

Nothing outside this module restates one of these. The column layout is derived
from the rule in docs/rail/info_kit.md section 2.1 rather than listed out, so a
schema correction is a one-line edit here rather than a hunt through the package.

Measured values carry the figure they were measured at; see
.claude/memory/rail-plan.md for how each was arrived at.
"""

import math

SUBSYSTEM_KEY = "rail"

# --- acquisition -----------------------------------------------------------

SAMPLE_RATE_HZ = 10_000
SAMPLES_PER_FILE = 10_000
QUANTISATION_STEP = 50 / 4096  # 12-bit ADC over +/-25 m/s^2; every sample is a multiple

# --- column layout ---------------------------------------------------------

CARS = 8
POSITIONS_PER_CAR = 8
CHANNELS_PER_BOX = 2  # vibration, then shock
N_AXLE_BOXES = CARS * POSITIONS_PER_CAR
SPEED_COLUMN = 0
N_COLUMNS = 1 + N_AXLE_BOXES * CHANNELS_PER_BOX

# Box order is car-major: car 1 positions 1-8, then car 2, and so on.
BOX_CARS = tuple(car for car in range(1, CARS + 1) for _ in range(POSITIONS_PER_CAR))
BOX_POSITIONS = tuple(pos for _ in range(CARS) for pos in range(1, POSITIONS_PER_CAR + 1))

VIBRATION_COLUMNS = tuple(1 + box * CHANNELS_PER_BOX for box in range(N_AXLE_BOXES))
SHOCK_COLUMNS = tuple(column + 1 for column in VIBRATION_COLUMNS)

# Positions 1,3,5,7 run along the Side I rail and 2,4,6,8 along Side II, so each
# side is observed by 32 boxes -- four per car, all eight crossing the same track.
SIDE_I_BOXES = tuple(i for i, pos in enumerate(BOX_POSITIONS) if pos % 2 == 1)
SIDE_II_BOXES = tuple(i for i, pos in enumerate(BOX_POSITIONS) if pos % 2 == 0)
SIDE_BOXES = (SIDE_I_BOXES, SIDE_II_BOXES)

SPEED_HEADER = "Rotating speed"
VIBRATION_HEADER = "Vibration of bearing in position {position} of car {car}"
SHOCK_HEADER = "Shock of bearing in position {position} of car {car}"
EXPECTED_HEADERS = (SPEED_HEADER,) + tuple(
    template.format(position=position, car=car)
    for car, position in zip(BOX_CARS, BOX_POSITIONS)
    for template in (VIBRATION_HEADER, SHOCK_HEADER)
)

# --- tachometer ------------------------------------------------------------

TACHOMETER_TEETH = 90
WHEEL_DIAMETER_M = 0.85
WHEEL_CIRCUMFERENCE_M = math.pi * WHEEL_DIAMETER_M
EDGES_PER_TOOTH = 2  # the output toggles as a tooth enters and again as it leaves

# Below this the train is not moving and wavelength = speed / frequency is undefined.
# 44 training files sit here, 38 of them with no tachometer edges at all; all are Normal.
STATIONARY_SPEED_MS = 0.5

# The slowest fault file in training. 133 of 234 Normal files sit below it, so
# "slow implies Normal" is free on more than half of Normal and never wrong --
# scoring the subset at or above this is the figure that confound cannot flatter.
FAST_SPEED_MS = 9.70

# --- labels ----------------------------------------------------------------

LABEL_COLUMNS = ("filename", "label")  # Train_Labels.csv, one row per training file

LABEL_NORMAL = "Normal"
LABEL_SIDE_I = "Side I"
LABEL_SIDE_II = "Side II"
LABELS = (LABEL_NORMAL, LABEL_SIDE_I, LABEL_SIDE_II)
SIDE_LABELS = (LABEL_SIDE_I, LABEL_SIDE_II)  # index-aligned with SIDE_BOXES

# What every file is called when no checkpoint exists. Also the majority class,
# so this is the 0.33 macro-F1 floor rather than an arbitrary guess.
FALLBACK_LABEL = LABEL_NORMAL

PREDICTION_COLUMNS = ("file_id", "prediction")

# Byte-identical to Train107.csv and Train165.csv respectively, both Normal.
# Excluded from training so a fold cannot score against its own example.
DUPLICATE_FILES = ("Train115.csv", "Train187.csv")

# --- spectra ---------------------------------------------------------------

# Corrugation excites f = speed / wavelength, which at the measured speeds puts
# the band at 30-650 Hz. 4096 samples gives 2.44 Hz per bin; the 256-sample
# default would give 39 Hz and bury the bottom of that band in its first bin.
WELCH_NPERSEG = 4096

HZ_BAND_EDGES = (0, 50, 150, 400, 800, 1500, 3000, 5000)
WAVELENGTH_EDGES_M = (0.02, 0.03, 0.05, 0.08, 0.12, 0.20, 0.30, 0.50)

# --- features --------------------------------------------------------------

CHANNEL_NAMES = ("vibration", "shock")  # separate feature blocks; never pooled

# Only some of a side's 32 boxes cross the corrugated stretch, so the aggregate
# has to be extreme-value; a robust one discards exactly those boxes.
AGGREGATE_PERCENTILE = 90

# Which of them a side is summarised by. The median was measured and dropped: it
# is a tie on macro F1 (+0.007 on 100 fresh folds, the interval straddling zero)
# with Side I consistently but unprovably better, so it goes as a simplification
# rather than as a gain -- 228 features against 342 for the same score.
AGGREGATES = ("max", f"p{AGGREGATE_PERCENTILE}")

# Keeps log10 finite for a dead channel, far below the quantisation step.
NUMERICAL_FLOOR = 1e-12

# --- artefacts -------------------------------------------------------------

FEATURE_CACHE_NAME = "features_train.npz"
CHECKPOINT_NAME = "classifier.pkl"

# The constants that change what a feature *is* without changing what it is
# *called*. Band edges and the percentile are already in the column names; these
# are not, so the cache and the checkpoint store this string too. Retuning the
# Welch window and fitting on yesterday's numbers is the failure that survives
# every check and surfaces only in the submitted CSV.
#
# SIDE_BOXES is in here because it is the worst of them: flipping the parity rule
# swaps the two rails while leaving every column name spelled exactly the same,
# and telling Side I from Side II is the entire task.
#
# AGGREGATES is deliberately NOT in here: it is spelled out in every column name,
# so dropping one is a mismatch the names catch on their own.
FEATURE_FINGERPRINT = "|".join(
    str(value)
    for value in (
        SAMPLE_RATE_HZ,
        WELCH_NPERSEG,
        STATIONARY_SPEED_MS,
        NUMERICAL_FLOOR,
        TACHOMETER_TEETH,
        WHEEL_DIAMETER_M,
        EDGES_PER_TOOTH,
        SIDE_BOXES,
    )
)

# --- model -----------------------------------------------------------------

CV_SPLITS = 5
CV_REPEATS = 10  # macro F1 here swings +/-0.04 on fold assignment; 5 repeats is too few
MODEL_MAX_ITER = 300
MODEL_CLASS_WEIGHT = "balanced"

# The linear comparison, not a candidate to ship. Penalised hard because it sees
# 228 features against 270 files; C chosen by CV, unlike the booster's defaults.
# The figure it was measured at was 342 against 272 -- see rail-plan.md's model
# comparison, which is quoted from that run and has not been re-measured since.
LINEAR_C = 0.1
LINEAR_MAX_ITER = 1000
