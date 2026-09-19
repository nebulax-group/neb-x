"""The normalised ratio is what makes the decision transfer between doors."""

import pandas as pd

from src.common import config as common_config
from src.common.io import read_table
from src.door import config, dataset, features


def test_one_row_per_cycle_aligned_with_bounds():
    from src.door import segment

    stream = read_table(common_config.TRAIN_PATHS["door"])
    table = features.build(stream)
    bounds = segment.segment_bounds(stream)
    assert len(table) == len(bounds)
    assert list(table["operation"]) == list(bounds["operation"])


def test_ratio_separates_the_two_classes_with_no_overlap():
    stream, _, status = dataset.labelled_segments()
    table = features.build(stream)
    abnormal = table.loc[(status == config.LABEL_ABNORMAL).values, "ratio"]
    normal = table.loc[(status == config.LABEL_NORMAL).values, "ratio"]
    assert normal.max() < abnormal.min(), "the ratio must separate the classes cleanly"


def test_the_documented_threshold_makes_no_training_errors():
    stream, _, status = dataset.labelled_segments()
    table = features.build(stream)
    predicted = (table["ratio"] > config.RATIO_THRESHOLD).values
    actual = (status == config.LABEL_ABNORMAL).values
    assert (predicted != actual).sum() == 0


def test_ratio_is_invariant_to_a_current_offset():
    """A door that simply draws more current must not change any decision.

    This is the measured reason the design normalises per stream: scaling the raw
    current by 0.85-1.20 costs a raw milliamp threshold up to 80 of 110 segments,
    and costs this feature nothing.
    """
    stream, _, status = dataset.labelled_segments()
    actual = (status == config.LABEL_ABNORMAL).values
    for factor in (0.85, 0.90, 0.95, 1.05, 1.10, 1.20):
        shifted = stream.copy()
        shifted[config.COLUMN_CURRENT] = shifted[config.COLUMN_CURRENT] * factor
        table = features.build(shifted)
        predicted = (table["ratio"] > config.RATIO_THRESHOLD).values
        assert (predicted != actual).sum() == 0, f"failed at factor {factor}"


def test_the_median_comes_from_the_stream_being_predicted():
    """Each operation's ratios are centred on that operation's own baseline within
    this file - a median of exactly 1.0 is only true if the baseline used to compute
    the ratio was recomputed from this stream, not carried over from another one."""
    stream = read_table(common_config.TEST_PATHS["door"])
    base = features.build(stream)
    assert base.groupby("operation")["ratio"].median().round(6).eq(1.0).all()
