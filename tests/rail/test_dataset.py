"""Reading a file wrong is the failure that survives every later check.

Two channels at different scales are interleaved one column apart, so an
off-by-one in the split hands the model shock where it expects vibration and
nothing downstream can tell. The malformed-file cases are here too: each one has
to arrive as a sentence naming the file, because each one reaches a reader.
"""

import numpy as np
import pandas as pd
import pytest

from src.rail import config, dataset, validate


def write_recording(path, rows=config.SAMPLES_PER_FILE, columns=None, values=0.0):
    """A syntactically valid rail CSV, wrong in exactly the way asked for."""
    columns = config.EXPECTED_HEADERS if columns is None else columns
    frame = pd.DataFrame(np.full((rows, len(columns)), values), columns=columns)
    frame.to_csv(path, index=False)
    return path


def test_a_recording_splits_into_one_speed_channel_and_two_box_matrices(side_i):
    assert side_i.speed_channel.shape == (config.SAMPLES_PER_FILE,)
    assert side_i.vibration.shape == (config.SAMPLES_PER_FILE, config.N_AXLE_BOXES)
    assert side_i.shock.shape == side_i.vibration.shape
    assert side_i.source_name == "Train62.csv"
    assert np.isfinite(side_i.vibration).all() and np.isfinite(side_i.shock).all()


def test_the_two_channels_are_different_measurements_and_not_the_same_slice(side_i):
    """Shock reads ~7x louder than vibration. Reading the interleave one column
    out would put one where the other belongs, with both shapes still correct."""
    vibration = float(np.sqrt(np.square(side_i.vibration).mean()))
    shock = float(np.sqrt(np.square(side_i.shock).mean()))
    assert vibration < shock
    assert not np.array_equal(side_i.vibration, side_i.shock)


def test_the_accelerometer_channels_arrive_on_the_documented_adc_grid(side_i):
    """Every sample is a multiple of 50/4096: a 12-bit ADC over +/-25 m/s^2.

    The tachometer is excluded deliberately -- it is a logic level, not a
    measurement, and does not sit on that grid.
    """
    for channel in (side_i.vibration, side_i.shock):
        steps = channel / config.QUANTISATION_STEP
        assert np.allclose(steps, np.round(steps), atol=1e-6)


def test_a_file_from_another_system_is_named_along_with_what_it_is_missing(tmp_path):
    path = write_recording(tmp_path / "notrail.csv", rows=3, columns=["a", "b"])
    with pytest.raises(ValueError, match=r"notrail\.csv .*expected 129 columns, found 2"):
        dataset.load_recording(path)


def test_a_renamed_column_is_reported_by_position_with_both_names(tmp_path):
    columns = list(config.EXPECTED_HEADERS)
    columns[7] = "Vibration of bearing in position 9 of car 1"
    path = write_recording(tmp_path / "renamed.csv", rows=2, columns=columns)
    mismatch = dataset.describe_header_mismatch(tuple(columns))
    assert "column 7" in mismatch and "position 9" in mismatch
    with pytest.raises(ValueError, match="column 7"):
        dataset.load_recording(path)


def test_a_correct_header_reports_no_mismatch():
    assert dataset.describe_header_mismatch(config.EXPECTED_HEADERS) == ""


def test_a_truncated_export_says_how_many_samples_it_actually_holds(tmp_path):
    path = write_recording(tmp_path / "short.csv", rows=5)
    with pytest.raises(ValueError, match=r"short\.csv holds 5 samples, expected 10000"):
        dataset.load_recording(path)


def test_a_hole_in_one_channel_is_refused_rather_than_spread_through_welch(tmp_path):
    """A NaN reaches every band of that box through the PSD without a trace."""
    frame = pd.DataFrame(
        np.zeros((config.SAMPLES_PER_FILE, config.N_COLUMNS)),
        columns=config.EXPECTED_HEADERS,
    )
    frame.iloc[11, 42] = np.nan
    path = tmp_path / "holey.csv"
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match=r"holey\.csv contains missing or non-finite"):
        dataset.load_recording(path)


def test_the_header_check_and_the_full_read_answer_a_bad_file_in_the_same_words(tmp_path):
    """dataset.py keeps one wording because two callers raise it, and a reader who
    fixes the file and uploads it again must not be told something different."""
    path = write_recording(tmp_path / "notrail.csv", rows=3, columns=["a", "b"])
    with pytest.raises(ValueError) as from_validate:
        validate.validate([path])
    with pytest.raises(ValueError) as from_load:
        dataset.load_recording(path)
    assert str(from_validate.value) == str(from_load.value)


def test_reading_a_header_parses_none_of_the_rows_beneath_it(side_i_path):
    assert dataset.read_header(side_i_path) == config.EXPECTED_HEADERS


def test_the_labels_are_the_documented_two_columns_and_three_words(labels):
    assert labels.index.name == config.LABEL_COLUMNS[0]
    assert set(labels) == set(config.LABELS)
    assert not labels.index.duplicated().any()
    assert len(labels) == 272


def test_the_class_balance_is_the_one_every_reported_figure_was_measured_at(labels):
    """234 / 14 / 24. Predicting Normal everywhere is 0.308 macro F1 at this
    balance, which is the floor every improvement in the write-up is read against."""
    counts = labels.value_counts()
    assert (counts[config.LABEL_NORMAL], counts[config.LABEL_SIDE_I], counts[config.LABEL_SIDE_II]) == (234, 14, 24)


def test_a_label_outside_the_vocabulary_is_refused(tmp_path, monkeypatch):
    path = tmp_path / "Train_Labels.csv"
    pd.DataFrame({"filename": ["Train1.csv"], "label": ["Side III"]}).to_csv(path, index=False)
    monkeypatch.setitem(dataset.LABEL_PATHS, config.SUBSYSTEM_KEY, path)
    with pytest.raises(ValueError, match=r"labels outside the vocabulary: \['Side III'\]"):
        dataset.load_labels()


def test_a_file_labelled_twice_is_refused_rather_than_silently_deduplicated(tmp_path, monkeypatch):
    path = tmp_path / "Train_Labels.csv"
    pd.DataFrame(
        {"filename": ["Train1.csv", "Train1.csv"], "label": ["Normal", "Side I"]}
    ).to_csv(path, index=False)
    monkeypatch.setitem(dataset.LABEL_PATHS, config.SUBSYSTEM_KEY, path)
    with pytest.raises(ValueError, match="more than once"):
        dataset.load_labels()
