"""The signal must rank the true faulty car first on every same-schema case."""

import pandas as pd

from src.acv import config, dataset, features, predict, rank
from src.common import config as common_config
from src.submission import validate


def _score_case(path):
    frame, cars = dataset.load_case(path)
    excess = features.temperature_excess(frame, cars)
    return rank.rank_cars(excess)


def test_leave_one_case_out_ranks_the_true_car_first_every_time():
    labels = dataset.load_labels().set_index(config.LABEL_FILENAME_COLUMN)
    scores = []
    for path in dataset.validation_case_paths():
        order = _score_case(path)
        truth = labels.loc[path.name, config.LABEL_CAR_COLUMN]
        position = order.index(truth) + 1
        scores.append((len(order) - (position - 1)) / len(order))
        assert position == 1, f"{path.name}: true car {truth} ranked {position}"
    assert sum(scores) / len(scores) == 1.0


def test_every_car_appears_exactly_once_in_the_ranking():
    for path in dataset.validation_case_paths():
        order = _score_case(path)
        assert len(order) == len(set(order)) == 8


def test_car_ids_keep_their_leading_zero_in_the_output():
    frame = predict.predict(dataset.test_case_paths())
    ranked = frame["ranked_cars"].iloc[0]
    assert ranked.split(config.RANKED_CARS_SEPARATOR) == [
        "01", "03", "07", "04", "08", "06", "02", "05"
    ]


def test_the_submission_has_one_row_naming_the_source_file_verbatim(tmp_path):
    frame = predict.predict(dataset.test_case_paths())
    assert len(frame) == 1
    assert frame["file_id"].iloc[0] == "acv_test_case.xlsx"
    assert list(frame.columns) == list(config.SUBMISSION_COLUMNS)

    # Written out and checked as a file, with the real input folder supplied, so the
    # validator's file_id check runs against the filenames actually on disk.
    path = tmp_path / common_config.PREDICTION_FILENAMES["acv"]
    frame.to_csv(path, index=False)
    assert validate.validate(path, common_config.TEST_PATHS["acv"]) == []


def test_a_car_with_no_usable_signal_is_ranked_last_not_dropped():
    """A NaN score must never make its car missing from ranked_cars - that scores zero."""
    scores = pd.Series({"03": 1.0, "01": 2.0, "04": float("nan"), "02": 0.5})
    order = rank.rank_cars(scores)
    assert order == ["01", "03", "02", "04"]
    assert "04" in order


def test_duty_cycle_is_a_fraction_for_every_car():
    for path in dataset.validation_case_paths():
        frame, cars = dataset.load_case(path)
        duty = features.cooling_duty_cycle(frame, cars)
        assert len(duty) == 8
        assert duty.between(0.0, 1.0).all()
