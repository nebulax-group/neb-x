"""predict() is the whole integration contract, and the CSV it writes is graded.

Two things are checked here that nothing else can: that the rows match the
schema the organisers ship, and that every way of arriving with the wrong
checkpoint stops rather than answering. A model fitted on different columns
still predicts -- it just predicts whatever those columns happen to mean now,
and that reaches the leaderboard as a score.
"""

import pickle

import pandas as pd
import pytest

from src.common.config import EXAMPLE_PREDICTION_PATHS, PREDICTION_PATHS
from src.common.io import read_table
from src.rail import config, features, predict, train


def doctored(checkpoint: dict, path, **changes):
    """The real checkpoint with one field spoiled, written where predict looks."""
    with path.open("wb") as handle:
        pickle.dump({**checkpoint, **changes}, handle)
    return path


def test_the_checkpoint_is_written_and_read_at_the_same_derived_path():
    """train.py and predict.py compose this from the same two owned constants
    rather than importing it from each other. Composed differently, training
    would succeed and predicting would report no model at all."""
    assert predict.CHECKPOINT_PATH == train.CHECKPOINT_PATH
    assert predict.CHECKPOINT_PATH.name == config.CHECKPOINT_NAME


def test_the_rows_match_the_schema_as_the_organisers_ship_it(held_out_paths, checkpoint):
    example = read_table(EXAMPLE_PREDICTION_PATHS[config.SUBSYSTEM_KEY])
    rows = predict.predict(held_out_paths, checkpoint)
    assert list(rows.columns) == list(example.columns) == list(config.PREDICTION_COLUMNS)
    assert set(rows[config.PREDICTION_COLUMNS[1]]) <= set(config.LABELS)
    assert predict.DEFAULT_OUTPUT_PATH == PREDICTION_PATHS[config.SUBSYSTEM_KEY]
    assert predict.DEFAULT_OUTPUT_PATH.name == "rail_predictions.csv"


def test_file_id_is_the_shipped_filename_and_the_rows_keep_the_order_given(
    held_out_paths, checkpoint
):
    """The organisers match on file_id exactly, and the held-out names are
    Test1.csv .. Test68.csv -- capital T, not zero-padded, not re-derived."""
    reversed_inputs = list(reversed(held_out_paths))
    rows = predict.predict(reversed_inputs, checkpoint)
    assert list(rows[config.PREDICTION_COLUMNS[0]]) == [p.name for p in reversed_inputs]


def test_predicting_on_nothing_is_refused_before_a_model_is_loaded():
    with pytest.raises(ValueError, match="No rail input files"):
        predict.predict([])


def test_a_missing_checkpoint_names_the_command_that_makes_one(tmp_path, monkeypatch):
    monkeypatch.setattr(predict, "CHECKPOINT_PATH", tmp_path / "absent.pkl")
    with pytest.raises(FileNotFoundError, match=r"python -m src\.rail\.train"):
        predict.load_checkpoint()


def test_a_checkpoint_fitted_on_other_columns_refuses_to_predict(
    tmp_path, monkeypatch, checkpoint
):
    path = doctored(checkpoint, tmp_path / "renamed.pkl", columns=("something_else",))
    monkeypatch.setattr(predict, "CHECKPOINT_PATH", path)
    with pytest.raises(ValueError, match=r"--refresh"):
        predict.load_checkpoint()


def test_a_checkpoint_fitted_under_other_settings_refuses_too(tmp_path, monkeypatch, checkpoint):
    """The names miss this one entirely: retuning the Welch window or flipping
    the side parity changes what every column holds and renames none of them."""
    path = doctored(checkpoint, tmp_path / "retuned.pkl", fingerprint="0|0|0")
    monkeypatch.setattr(predict, "CHECKPOINT_PATH", path)
    with pytest.raises(ValueError, match=r"different features"):
        predict.load_checkpoint()


def test_the_shipped_checkpoint_passes_both_guards(checkpoint):
    assert tuple(checkpoint["columns"]) == features.FEATURE_NAMES
    assert checkpoint["fingerprint"] == config.FEATURE_FINGERPRINT
    assert checkpoint["excluded_files"] == config.DUPLICATE_FILES
    assert set(checkpoint["estimator"].classes_) == set(config.LABELS)


def test_the_written_csv_carries_no_index_column(tmp_path):
    frame = pd.DataFrame(
        {config.PREDICTION_COLUMNS[0]: ["Test1.csv"], config.PREDICTION_COLUMNS[1]: ["Normal"]}
    )
    path = predict.write_predictions(frame, tmp_path / "out" / "rail_predictions.csv")
    assert path.read_text().splitlines()[0] == "file_id,prediction"
    pd.testing.assert_frame_equal(read_table(path), frame)


def test_the_command_line_writes_the_csv_for_one_recording(tmp_path, monkeypatch, held_out_paths):
    output = tmp_path / "rail_predictions.csv"
    monkeypatch.setattr(
        "sys.argv", ["predict", "--input", str(held_out_paths[0]), "--output", str(output)]
    )
    predict.main()
    rows = read_table(output)
    assert list(rows[config.PREDICTION_COLUMNS[0]]) == [held_out_paths[0].name]


def test_a_broken_checkpoint_leaves_the_command_line_with_a_sentence_not_a_traceback(
    tmp_path, monkeypatch, held_out_paths
):
    """main() catches the several ways a checkpoint from another version fails,
    and every one of them has to read as a sentence to whoever ran the script."""
    broken = tmp_path / "broken.pkl"
    with broken.open("wb") as handle:
        pickle.dump("not a checkpoint at all", handle)
    monkeypatch.setattr(predict, "CHECKPOINT_PATH", broken)
    monkeypatch.setattr(
        "sys.argv",
        ["predict", "--input", str(held_out_paths[0]), "--output", str(tmp_path / "out.csv")],
    )
    with pytest.raises(SystemExit, match="Rail prediction failed"):
        predict.main()
