"""The column layout is derived from a rule, so the rule is what gets checked.

config.py builds 129 column names out of a parity rule instead of listing them,
and the whole task rests on that rule: flipping it swaps Side I for Side II while
every column keeps the name it had, every test that checks a shape still passes,
and the only place it shows is the submitted CSV. So the derivation is read back
out of the organisers' own header text here rather than restated.
"""

import re
import string

import pytest

from src.app import config as app_config
from src.common.config import TEST_PATHS, TRAIN_PATHS
from src.common.io import list_data_files
from src.rail import config, dataset

_HEADER = re.compile(r"^(Vibration|Shock) of bearing in position (\d) of car (\d)$")


def test_the_column_count_is_the_speed_channel_plus_two_per_axle_box():
    assert config.N_AXLE_BOXES == 64
    assert config.N_COLUMNS == 129
    assert len(config.EXPECTED_HEADERS) == config.N_COLUMNS
    assert config.EXPECTED_HEADERS[config.SPEED_COLUMN] == config.SPEED_HEADER


def test_vibration_and_shock_interleave_and_between_them_cover_every_column():
    assert len(config.VIBRATION_COLUMNS) == len(config.SHOCK_COLUMNS) == config.N_AXLE_BOXES
    assert set(config.VIBRATION_COLUMNS).isdisjoint(config.SHOCK_COLUMNS)
    covered = set(config.VIBRATION_COLUMNS) | set(config.SHOCK_COLUMNS) | {config.SPEED_COLUMN}
    assert covered == set(range(config.N_COLUMNS))
    # Interleaved, not blocked: shock is the column after its own box's vibration.
    assert all(
        shock == vibration + 1
        for vibration, shock in zip(config.VIBRATION_COLUMNS, config.SHOCK_COLUMNS)
    )


def test_each_side_is_thirty_two_boxes_and_the_two_do_not_overlap():
    assert len(config.SIDE_I_BOXES) == len(config.SIDE_II_BOXES) == config.N_AXLE_BOXES // 2
    assert set(config.SIDE_I_BOXES).isdisjoint(config.SIDE_II_BOXES)
    assert set(config.SIDE_I_BOXES) | set(config.SIDE_II_BOXES) == set(range(config.N_AXLE_BOXES))
    assert config.SIDE_BOXES == (config.SIDE_I_BOXES, config.SIDE_II_BOXES)
    # features.py and explain.py both index SIDE_BOXES with SIDE_LABELS' index.
    assert config.SIDE_LABELS == (config.LABEL_SIDE_I, config.LABEL_SIDE_II)
    assert len(config.SIDE_LABELS) == len(config.SIDE_BOXES)


def test_the_side_of_a_box_is_the_parity_of_the_position_the_header_gives_it():
    """Read out of the organisers' words, not out of BOX_POSITIONS.

    This is the assertion that a swapped pair of rails cannot survive: it takes
    the position from the column name itself and checks which side config filed
    that box under.
    """
    for box in range(config.N_AXLE_BOXES):
        name = config.EXPECTED_HEADERS[config.VIBRATION_COLUMNS[box]]
        matched = _HEADER.match(name)
        assert matched, name
        kind, position, car = matched.group(1), int(matched.group(2)), int(matched.group(3))
        assert kind == "Vibration"
        assert (box in config.SIDE_I_BOXES) == (position % 2 == 1)
        assert (box in config.SIDE_II_BOXES) == (position % 2 == 0)
        assert config.BOX_POSITIONS[box] == position
        assert config.BOX_CARS[box] == car
    # Four boxes of each side per car, which is what makes the contrast a
    # comparison of the two rails rather than of two parts of the train.
    for car in range(1, config.CARS + 1):
        for side in config.SIDE_BOXES:
            assert sum(config.BOX_CARS[box] == car for box in side) == 4


@pytest.mark.parametrize("folder", ["train", "test"])
def test_every_shipped_file_carries_exactly_the_derived_header(folder):
    """All 340 of them, because one mis-split file is one silently swapped rail.

    Only the names are read: pandas parses no rows for nrows=0, so this is 5 ms
    a file rather than the 130 ms a full parse would cost.
    """
    paths = {"train": TRAIN_PATHS, "test": TEST_PATHS}[folder][config.SUBSYSTEM_KEY]
    mismatched = {
        path.name: dataset.describe_header_mismatch(dataset.read_header(path))
        for path in list_data_files(paths)
    }
    assert {name: why for name, why in mismatched.items() if why} == {}


def test_the_speed_thresholds_are_ordered_and_the_labels_are_the_shipped_three():
    assert 0 < config.STATIONARY_SPEED_MS < config.FAST_SPEED_MS
    assert config.LABELS == ("Normal", "Side I", "Side II")
    assert config.PREDICTION_COLUMNS == ("file_id", "prediction")


def test_every_label_has_a_severity_the_app_has_a_colour_for():
    """A severity the palette cannot paint renders as a verdict with no marking."""
    assert set(config.SEVERITIES) == set(config.LABELS)
    assert set(config.SEVERITIES.values()) <= set(app_config.SEVERITY_WORDS)
    # A named rail is a caution and never an alert: the model says which rail is
    # corrugated, not how worn it is, so there is no depth to raise an alert on.
    assert set(config.SEVERITIES.values()) == {config.SEVERITY_CLEAR, config.SEVERITY_CAUTION}


def test_every_recommendation_fills_in_from_what_explain_supplies():
    """explain.py formats these with rail and file, and nothing else exists to pass.

    A placeholder nobody fills reaches the screen as a literal brace, and a
    placeholder nobody defined raises KeyError inside the app's render.
    """
    supplied = {"rail", "file"}
    for severity, steps in config.RECOMMENDATIONS.items():
        assert severity in config.SEVERITIES.values()
        for text in (steps["title"], *steps["steps"]):
            named = {
                field
                for _, field, _, _ in string.Formatter().parse(text)
                if field is not None
            }
            assert named <= supplied, (severity, named - supplied)
            assert "{" not in text.format(rail="Side I", file="Test1.csv")
