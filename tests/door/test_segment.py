"""Segmentation must reproduce the answer file exactly - that is what makes IoU 1.0."""

import pandas as pd

from src.common import config as common_config
from src.common.io import read_table
from src.door import config, segment


def test_train_splits_into_the_documented_number_of_segments():
    frame = read_table(common_config.TRAIN_PATHS["door"])
    bounds = segment.segment_bounds(frame)
    assert len(bounds) == config.EXPECTED_TRAIN_SEGMENTS


def test_boundaries_match_the_answer_file_exactly():
    frame = read_table(common_config.TRAIN_PATHS["door"])
    bounds = segment.segment_bounds(frame)
    answer = read_table(common_config.LABEL_PATHS["door"])

    assert list(bounds["start_time"]) == list(answer["start_time"])
    assert list(bounds["end_time"]) == list(answer["end_time"])
    assert list(bounds["n_rows"]) == list(answer["n_rows"])


def test_operation_is_recovered_from_the_movement_flags():
    frame = read_table(common_config.TRAIN_PATHS["door"])
    bounds = segment.segment_bounds(frame)
    answer = read_table(common_config.LABEL_PATHS["door"])
    assert list(bounds["operation"]) == list(answer["operation"])


def test_timestamps_are_the_source_strings_not_reformatted():
    frame = read_table(common_config.TRAIN_PATHS["door"])
    bounds = segment.segment_bounds(frame)
    # The native format is not zero padded; a formatter round trip would produce 2023-07-05.
    assert bounds["start_time"].iloc[0] == frame[config.COLUMN_TIME].iloc[0]
    assert "2023-7-5" in bounds["start_time"].iloc[0]


def test_test_stream_splits_into_thirty_eight_segments():
    frame = read_table(common_config.TEST_PATHS["door"])
    assert len(segment.segment_bounds(frame)) == 38
