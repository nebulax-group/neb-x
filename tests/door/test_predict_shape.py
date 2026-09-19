"""The predictor's output shape is a submission contract, checked before modelling."""

from src.common import config as common_config
from src.door import config, predict
from src.submission import validate


def test_predict_returns_one_row_per_test_cycle(tmp_path):
    frame = predict.predict([common_config.TEST_PATHS["door"]])
    assert len(frame) == 38
    assert list(frame.columns) == list(config.SUBMISSION_COLUMNS)

    # The shared validator reads a file rather than a frame, because the CSV on disk
    # is what gets submitted - a frame can be right while to_csv still spoils it.
    path = tmp_path / common_config.PREDICTION_FILENAMES["door"]
    frame.to_csv(path, index=False)
    assert validate.validate(path) == []


def test_predictions_use_only_the_official_label_vocabulary():
    frame = predict.predict([common_config.TEST_PATHS["door"]])
    assert set(frame["prediction"]) <= {config.LABEL_NORMAL, config.LABEL_ABNORMAL}


def test_timestamps_are_echoed_from_the_source_file():
    from src.common.io import read_table

    stream = read_table(common_config.TEST_PATHS["door"])
    frame = predict.predict([common_config.TEST_PATHS["door"]])
    source_times = set(stream[config.COLUMN_TIME])
    assert set(frame["start_time"]) <= source_times
    assert set(frame["end_time"]) <= source_times
