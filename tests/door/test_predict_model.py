"""The shipped predictor must match the documented rule on the real test stream."""

from src.common import config as common_config
from src.common.io import read_table
from src.door import config, features, predict


def test_predictor_and_threshold_rule_agree_on_the_test_stream():
    stream = read_table(common_config.TEST_PATHS["door"])
    frame = predict.predict([common_config.TEST_PATHS["door"]])
    table = features.build(stream)
    rule = [
        config.LABEL_ABNORMAL if r > config.RATIO_THRESHOLD else config.LABEL_NORMAL
        for r in table["ratio"]
    ]
    assert list(frame["prediction"]) == rule


def test_the_test_stream_yields_the_expected_abnormal_count():
    """Eight cycles sit far above their own baseline; the ninth-highest is at 1.067."""
    frame = predict.predict([common_config.TEST_PATHS["door"]])
    assert (frame["prediction"] == config.LABEL_ABNORMAL).sum() == 8
