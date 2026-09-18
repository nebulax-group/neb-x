"""The signal must rank the true faulty car first on every same-schema case."""

from src.acv import config, dataset, features, predict, rank
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


def test_the_submission_has_one_row_naming_the_source_file_verbatim():
    frame = predict.predict(dataset.test_case_paths())
    assert len(frame) == 1
    assert frame["file_id"].iloc[0] == "acv_test_case.xlsx"
    assert list(frame.columns) == list(config.SUBMISSION_COLUMNS)
    validate.validate("acv", frame)


def test_duty_cycle_is_a_fraction_for_every_car():
    for path in dataset.validation_case_paths():
        frame, cars = dataset.load_case(path)
        duty = features.cooling_duty_cycle(frame, cars)
        assert len(duty) == 8
        assert duty.between(0.0, 1.0).all()
