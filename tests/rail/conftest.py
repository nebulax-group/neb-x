"""Real recordings, each named for the one property it is here to exercise.

A rail CSV is 21 MB and 0.13 s to parse, so these tests run on four named files
rather than on a search over the folder. Every fixture asserts the property its
file was picked for, which is the point of naming them: a change under
data/rail/ then fails here saying which fact moved, instead of quietly turning
the stationary test into a second moving one.

Nothing here fits a model. Rail's checkpoint takes minutes and is the one
artefact on the path to the graded CSV, so the tests read the real one and say
how to make it rather than writing a throwaway over the top of it -- which is
the opposite of Door's conftest, and for that reason.
"""

from pathlib import Path

import pytest

from src.common.config import TEST_PATHS, TRAIN_PATHS
from src.rail import config, dataset, predict
from src.rail.speed import estimate_speed

FILENAME, LABEL = config.LABEL_COLUMNS

# Chosen from the 272 training files by the speed their own tachometer reports.
STILL = "Train75.csv"  # 0.00 m/s, no tachometer edges at all; one of the 38
CRAWLING = "Train52.csv"  # 1.29 m/s: moving, but too slow to resolve the longest band
SIDE_I = "Train62.csv"  # 13.28 m/s, the rarest label
SIDE_II = "Train2.csv"  # 13.35 m/s

HELD_OUT = ("Test1.csv", "Test2.csv")


@pytest.fixture(scope="session")
def train_dir() -> Path:
    return TRAIN_PATHS[config.SUBSYSTEM_KEY]


@pytest.fixture(scope="session")
def held_out_paths() -> list[Path]:
    """Two of the 68 files the submission is actually scored on."""
    return [TEST_PATHS[config.SUBSYSTEM_KEY] / name for name in HELD_OUT]


@pytest.fixture(scope="session")
def labels():
    return dataset.load_labels().set_index(FILENAME)[LABEL]


def _load(train_dir: Path, name: str) -> dataset.Recording:
    return dataset.load_recording(train_dir / name)


@pytest.fixture(scope="session")
def still_path(train_dir) -> Path:
    return train_dir / STILL


@pytest.fixture(scope="session")
def still(train_dir, labels):
    """A file recorded with the train stopped, where wavelength is undefined."""
    recording = _load(train_dir, STILL)
    assert estimate_speed(recording.speed_channel) == 0.0, f"{STILL} is no longer stationary"
    assert labels[STILL] == config.LABEL_NORMAL
    return recording


@pytest.fixture(scope="session")
def crawling(train_dir, labels):
    """Moving, but below the speed at which every wavelength band catches a bin.

    The gap between this and ``still`` is where the two NaN branches part: one
    band is undefined here because Welch resolves nothing inside it, where every
    band is undefined on a stationary file because there is no wavelength at all.
    """
    recording = _load(train_dir, CRAWLING)
    speed = estimate_speed(recording.speed_channel)
    assert config.STATIONARY_SPEED_MS <= speed < config.FAST_SPEED_MS, speed
    return recording


@pytest.fixture(scope="session")
def side_i_path(train_dir, labels) -> Path:
    assert labels[SIDE_I] == config.LABEL_SIDE_I
    return train_dir / SIDE_I


@pytest.fixture(scope="session")
def side_ii_path(train_dir, labels) -> Path:
    assert labels[SIDE_II] == config.LABEL_SIDE_II
    return train_dir / SIDE_II


@pytest.fixture(scope="session")
def side_i(side_i_path, labels):
    """A fault file, fast enough that every band resolves and nothing is NaN."""
    recording = dataset.load_recording(side_i_path)
    assert estimate_speed(recording.speed_channel) >= config.FAST_SPEED_MS
    return recording


@pytest.fixture(scope="session")
def checkpoint() -> dict:
    """The real fitted model, or a failure naming the command that makes one.

    Skipping would leave the whole prediction path untested and say so only in a
    summary line nobody reads, which is the failure mode this suite exists for.
    """
    try:
        return predict.load_checkpoint()
    except (FileNotFoundError, ValueError) as error:
        pytest.fail(f"{error}", pytrace=False)
