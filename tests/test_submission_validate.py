"""A submission must match the shipped example's columns exactly."""

import pandas as pd
import pytest

from src.submission import validate


def test_accepts_a_correct_door_frame():
    frame = pd.DataFrame(
        {"start_time": ["2023-7-5-0-0-0-0"], "end_time": ["2023-7-5-0-0-3-700"],
         "prediction": ["Normal"]}
    )
    validate.validate("door", frame)


def test_rejects_a_missing_column():
    frame = pd.DataFrame({"start_time": ["x"], "end_time": ["y"]})
    with pytest.raises(ValueError, match="columns"):
        validate.validate("door", frame)


def test_rejects_a_reordered_or_extra_column():
    frame = pd.DataFrame(
        {"prediction": ["Normal"], "start_time": ["x"], "end_time": ["y"]}
    )
    with pytest.raises(ValueError, match="columns"):
        validate.validate("door", frame)


def test_rejects_an_empty_frame():
    frame = pd.DataFrame({"start_time": [], "end_time": [], "prediction": []})
    with pytest.raises(ValueError, match="empty"):
        validate.validate("door", frame)
