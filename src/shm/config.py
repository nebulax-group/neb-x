"""Every SHM dimension: file schema, label schema and target properties.

Paths come from ``src/common/config.py``; the one derived below names the
checkpoint this subsystem writes, which only SHM can know. Sampling
rate and stress units are not documented by the Info Kit, so they are absent
rather than guessed.
"""

from src.common.config import MODEL_DIRS

SUBSYSTEM_KEY = "shm"

FILE_ID_COLUMN = "file_id"
PREDICTION_COLUMN = "prediction"
PREDICTION_COLUMNS = (FILE_ID_COLUMN, PREDICTION_COLUMN)

LABEL_FILENAME_COLUMN = "filename"
LABEL_DAMAGE_COLUMN = "damage"
LABEL_COLUMNS = (LABEL_FILENAME_COLUMN, LABEL_DAMAGE_COLUMN)

# The dynamic-stress files ship with no header row and a single unnamed column.
STRESS_COLUMN_COUNT = 1
STRESS_DTYPE = "float64"
EXPECTED_SAMPLES_PER_FILE = 581_120

EXPECTED_TRAIN_FILES = 64
EXPECTED_TEST_FILES = 16

# Layout of the array returned by features.extract_cycles, shared by everything that
# reads it so the producer and the consumers cannot disagree about column order.
CYCLE_AMPLITUDE = 0
CYCLE_MEAN = 1
CYCLE_COUNT = 2
CYCLE_COLUMNS = 3

# Miner's linear rule: damage accumulates from zero and failure is reached at 1.
MIN_DAMAGE = 0.0
FAILURE_DAMAGE = 1.0

# Mean of the 64 training labels; the banked prediction until a model exists.
BASELINE_DAMAGE = 0.23

# S-N search space. The exponent is a material property rather than a free knob —
# EN 1993-1-9 puts welded steel between 3 and 5 — so the bounds only have to be
# wide enough that the optimum lands strictly inside them.
EXPONENT_MIN = 1.0
EXPONENT_MAX = 12.0
EXPONENT_COARSE_STEP = 0.25
EXPONENT_FINE_STEP = 0.01

# Checkpoint field names, so the trainer that writes one and the predictor that
# reads it cannot disagree about what the two fitted numbers are called.
MODEL_EXPONENT_KEY = "exponent"
MODEL_COEFFICIENT_KEY = "coefficient"
CHECKPOINT_FILENAME = "sn_curve.json"
CHECKPOINT_PATH = MODEL_DIRS[SUBSYSTEM_KEY] / CHECKPOINT_FILENAME
