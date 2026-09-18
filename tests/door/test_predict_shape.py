"""The predictor's output shape is a submission contract, checked before modelling."""

from src.common import config as common_config
from src.door import config, predict
from src.submission import validate


def test_predict_returns_one_row_per_test_cycle():
    frame = predict.predict([common_config.TEST_PATHS["door"]])
    assert len(frame) == 38
    assert list(frame.columns) == list(config.SUBMISSION_COLUMNS)
    validate.validate("door", frame)


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
