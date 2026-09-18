"""Shared constants and repository paths; subsystem schemas use their own config.

Paths are independent of the current working directory. Importing this module
creates no files or directories.
"""

from pathlib import Path

RANDOM_SEED = 42

SUBSYSTEMS = ("door", "acv", "rail", "shm")
CSV_EXTENSION = ".csv"
XLSX_EXTENSION = ".xlsx"
SUPPORTED_DATA_EXTENSIONS = (CSV_EXTENSION, XLSX_EXTENSION)
IGNORED_DATA_FILE_PREFIXES = (".", "~$")
DEFAULT_EXCEL_SHEET = 0

# The organisers' own column name, shared by every subsystem whose rows name a
# source file. Door is the exception and has no such column at all.
FILE_ID_COLUMN = "file_id"

PREDICTION_FILENAMES = {
    subsystem: f"{subsystem}_predictions{CSV_EXTENSION}" for subsystem in SUBSYSTEMS
}
PREDICTIONS_ARCHIVE_NAME = "predictions.zip"

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
DATA_DIR = REPO_ROOT / "data"
DOCS_DIR = REPO_ROOT / "docs"
REFERENCE_DIR = REPO_ROOT / "reference"
SUBMISSION_FORMAT_DIR = REFERENCE_DIR / "submission_format"
SCRIPTS_DIR = REPO_ROOT / "scripts"
STREAMLIT_CONFIG_PATH = REPO_ROOT / ".streamlit" / "config.toml"

OUTPUTS_DIR = REPO_ROOT / "outputs"
MODELS_DIR = OUTPUTS_DIR / "models"
PREDICTIONS_DIR = OUTPUTS_DIR / "predictions"
PLOTS_DIR = OUTPUTS_DIR / "plots"
LOGS_DIR = OUTPUTS_DIR / "logs"
SUBMISSION_DIR = OUTPUTS_DIR / "submission"
PREDICTIONS_ZIP_PATH = SUBMISSION_DIR / PREDICTIONS_ARCHIVE_NAME

DATA_DIRS = {subsystem: DATA_DIR / subsystem for subsystem in SUBSYSTEMS}

# Door's recordings and labels sit directly in its data folder.
TRAIN_PATHS = {
    subsystem: directory / ("Train.csv" if subsystem == "door" else "train")
    for subsystem, directory in DATA_DIRS.items()
}
TEST_PATHS = {
    subsystem: directory / ("Test.csv" if subsystem == "door" else "test")
    for subsystem, directory in DATA_DIRS.items()
}
LABEL_PATHS = {
    subsystem: directory
    / ("Train_Segments_Answer.csv" if subsystem == "door" else "Train_Labels.csv")
    for subsystem, directory in DATA_DIRS.items()
}

MODEL_DIRS = {subsystem: MODELS_DIR / subsystem for subsystem in SUBSYSTEMS}
PREDICTION_PATHS = {
    subsystem: PREDICTIONS_DIR / filename
    for subsystem, filename in PREDICTION_FILENAMES.items()
}
EXAMPLE_PREDICTION_PATHS = {
    subsystem: SUBMISSION_FORMAT_DIR / filename
    for subsystem, filename in PREDICTION_FILENAMES.items()
}
INFO_KIT_PATHS = {
    subsystem: DOCS_DIR / subsystem / "info_kit.md" for subsystem in SUBSYSTEMS
}
