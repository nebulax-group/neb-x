"""Cover src/submission/validate.py — shared code the whole submission depends on.

The validator is what stands between a CSV that looks right and a CSV that scores.
Every case below is a failure it exists to catch, written from the caller's side:
a file is handed over, and the problems come back as a list (empty means clean).

Filenames matter here. schema.for_file picks the schema from the file's own name,
because the name is part of the organisers' contract rather than a label chosen at
packaging time — so each fixture is written under its real submission filename.
"""

import pandas as pd

from src.common import config
from src.submission import validate

DOOR_NAME = config.PREDICTION_FILENAMES["door"]
ACV_NAME = config.PREDICTION_FILENAMES["acv"]

DOOR_ROWS = {
    "start_time": ["2023-7-5-0-0-0-0", "2023-7-5-0-0-23-999"],
    "end_time": ["2023-7-5-0-0-3-700", "2023-7-5-0-0-26-839"],
    "prediction": ["Normal", "Abnormal resistance"],
}


def _write(directory, name, frame, **kwargs):
    path = directory / name
    frame.to_csv(path, index=False, **kwargs)
    return path


def test_a_correct_door_file_reports_no_problems(tmp_path):
    path = _write(tmp_path, DOOR_NAME, pd.DataFrame(DOOR_ROWS))
    assert validate.validate(path) == []


def test_a_missing_column_is_caught(tmp_path):
    frame = pd.DataFrame(DOOR_ROWS).drop(columns=["prediction"])
    problems = validate.validate(_write(tmp_path, DOOR_NAME, frame))
    assert any("prediction" in problem for problem in problems)


def test_columns_in_the_wrong_order_are_caught(tmp_path):
    frame = pd.DataFrame(DOOR_ROWS)[["prediction", "start_time", "end_time"]]
    problems = validate.validate(_write(tmp_path, DOOR_NAME, frame))
    assert any("order" in problem.lower() for problem in problems)


def test_an_index_column_written_by_to_csv_is_caught(tmp_path):
    """The most common way a valid-looking file breaks: forgetting index=False."""
    path = tmp_path / DOOR_NAME
    pd.DataFrame(DOOR_ROWS).to_csv(path)  # deliberately keeps the index
    problems = validate.validate(path)
    assert any("index=False" in problem for problem in problems)


def test_a_blank_cell_is_caught(tmp_path):
    rows = {key: list(value) for key, value in DOOR_ROWS.items()}
    rows["prediction"][1] = ""
    problems = validate.validate(_write(tmp_path, DOOR_NAME, pd.DataFrame(rows)))
    assert any("empty" in problem.lower() for problem in problems)


def test_a_header_with_no_rows_is_caught(tmp_path):
    frame = pd.DataFrame({key: [] for key in DOOR_ROWS})
    problems = validate.validate(_write(tmp_path, DOOR_NAME, frame))
    assert any("no rows" in problem.lower() for problem in problems)


def test_a_file_named_something_else_is_rejected(tmp_path):
    path = _write(tmp_path, "predictions.csv", pd.DataFrame(DOOR_ROWS))
    problems = validate.validate(path)
    assert any("not a prediction filename" in problem.lower() for problem in problems)


def test_a_rebuilt_file_id_is_caught_against_the_real_inputs(tmp_path):
    """The failure that scores zero while every prediction is correct.

    ACV's file_id must echo the source filename. Here it is lowercased, which is
    exactly what a rebuilt name looks like, and the validator is given the real
    input folder to check against.
    """
    frame = pd.DataFrame(
        {"file_id": ["ACV_TEST_CASE.xlsx"], "ranked_cars": ["01|03|07|04|08|06|02|05"]}
    )
    problems = validate.validate(
        _write(tmp_path, ACV_NAME, frame), config.TEST_PATHS["acv"]
    )
    assert any("Echo the filename" in problem for problem in problems)


def test_the_real_acv_file_id_passes_the_same_check(tmp_path):
    frame = pd.DataFrame(
        {"file_id": ["acv_test_case.xlsx"], "ranked_cars": ["01|03|07|04|08|06|02|05"]}
    )
    problems = validate.validate(
        _write(tmp_path, ACV_NAME, frame), config.TEST_PATHS["acv"]
    )
    assert problems == []


def test_a_missing_file_is_reported_rather_than_raising(tmp_path):
    problems = validate.validate(tmp_path / DOOR_NAME)
    assert any("no such file" in problem.lower() for problem in problems)
