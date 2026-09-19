"""Cover src/submission/generate.py — the step that produces the CSVs we submit.

The whole point of that module is that a prediction file is never found, only made.
The cases below are the ways that guarantee breaks: a stale file trusted because
nothing overwrote it, one subsystem's fault taking the other three down with it,
and a CSV written with an index column, which scores zero while looking correct.

The predictors are stubbed here. What a subsystem predicts is its own package's
business and is tested there; what happens to the file afterwards is this one's.
"""

import pandas as pd
import pytest

from src.common import config
from src.submission import generate

ROWS = pd.DataFrame({"file_id": ["case01.csv", "case02.csv"], "prediction": [0.41, 0.62]})
SUBSYSTEM = "shm"


def _redirect(monkeypatch, tmp_path, subsystem=SUBSYSTEM, with_inputs=True):
    """Point one subsystem's inputs and output at tmp_path, and return the output."""
    output = tmp_path / "predictions" / config.PREDICTION_FILENAMES[subsystem]
    monkeypatch.setitem(generate.PREDICTION_PATHS, subsystem, output)

    inputs = tmp_path / "test" / subsystem
    if with_inputs:
        inputs.mkdir(parents=True)
        (inputs / "case01.csv").write_text("time,stress\n0,1\n")
    monkeypatch.setitem(generate.TEST_PATHS, subsystem, inputs)
    return output


def _stub_predictor(monkeypatch, result):
    """Stand in for src.<sub>.predict.predict; result may be a frame or an exception."""

    def predictor(inputs):
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(generate, "load_predictor", lambda subsystem: predictor)


def test_a_prediction_is_written_and_its_rows_counted(monkeypatch, tmp_path):
    output = _redirect(monkeypatch, tmp_path)
    _stub_predictor(monkeypatch, ROWS)

    outcome = generate.generate(SUBSYSTEM)

    assert outcome.written
    assert outcome.rows == len(ROWS)
    assert outcome.path == output
    assert output.exists()


def test_the_csv_carries_no_index_column(monkeypatch, tmp_path):
    """An index written by to_csv breaks the schema while the file still opens."""
    output = _redirect(monkeypatch, tmp_path)
    _stub_predictor(monkeypatch, ROWS)

    generate.generate(SUBSYSTEM)

    assert output.read_text().splitlines()[0] == "file_id,prediction"


def test_columns_and_values_reach_the_file_unchanged(monkeypatch, tmp_path):
    output = _redirect(monkeypatch, tmp_path)
    _stub_predictor(monkeypatch, ROWS)

    generate.generate(SUBSYSTEM)

    written = pd.read_csv(output)
    assert list(written.columns) == list(ROWS.columns)
    assert written["file_id"].tolist() == ROWS["file_id"].tolist()


def test_a_stale_file_is_overwritten_rather_than_trusted(monkeypatch, tmp_path):
    """The reason this module exists: whatever was there was made by another run."""
    output = _redirect(monkeypatch, tmp_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("file_id,prediction\nrubbish.csv,99999\n")
    _stub_predictor(monkeypatch, ROWS)

    generate.generate(SUBSYSTEM)

    assert "rubbish.csv" not in output.read_text()
    assert pd.read_csv(output)["file_id"].tolist() == ROWS["file_id"].tolist()


def test_a_missing_predictor_module_is_skipped_with_a_reason(monkeypatch, tmp_path):
    _redirect(monkeypatch, tmp_path, subsystem="rail")

    def absent(subsystem):
        raise ModuleNotFoundError("No module named 'src.rail.predict'")

    monkeypatch.setattr(generate, "load_predictor", absent)

    outcome = generate.generate("rail")

    assert not outcome.written
    assert "src.rail.predict" in outcome.reason


def test_missing_test_data_is_skipped_with_a_reason(monkeypatch, tmp_path):
    _redirect(monkeypatch, tmp_path, with_inputs=False)
    _stub_predictor(monkeypatch, ROWS)

    outcome = generate.generate(SUBSYSTEM)

    assert not outcome.written
    assert "test inputs" in outcome.reason


def test_a_missing_checkpoint_is_skipped_naming_what_was_raised(monkeypatch, tmp_path):
    _redirect(monkeypatch, tmp_path)
    _stub_predictor(monkeypatch, FileNotFoundError("No SHM model at sn_curve.json"))

    outcome = generate.generate(SUBSYSTEM)

    assert not outcome.written
    assert "FileNotFoundError" in outcome.reason
    assert "sn_curve.json" in outcome.reason


def test_any_other_failure_is_skipped_rather_than_raised(monkeypatch, tmp_path):
    _redirect(monkeypatch, tmp_path)
    _stub_predictor(monkeypatch, KeyError("stress"))

    outcome = generate.generate(SUBSYSTEM)

    assert not outcome.written
    assert "KeyError" in outcome.reason


def test_a_stale_file_is_discarded_when_its_subsystem_cannot_run(monkeypatch, tmp_path):
    """Nothing overwrites it, so leaving it would submit a prediction nobody made."""
    output = _redirect(monkeypatch, tmp_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("file_id,prediction\nrubbish.csv,99999\n")
    _stub_predictor(monkeypatch, FileNotFoundError("no checkpoint"))

    outcome = generate.generate(SUBSYSTEM)

    assert not output.exists()
    assert "discarded" in outcome.reason


def test_one_subsystem_failing_leaves_the_others_written(monkeypatch, tmp_path):
    outputs = {
        subsystem: _redirect(monkeypatch, tmp_path, subsystem=subsystem)
        for subsystem in config.SUBSYSTEMS
    }

    def by_subsystem(subsystem):
        if subsystem == "rail":
            raise ModuleNotFoundError("No module named 'src.rail.predict'")
        return lambda inputs: ROWS

    monkeypatch.setattr(generate, "load_predictor", by_subsystem)

    outcomes = {outcome.subsystem: outcome for outcome in generate.generate_all()}

    assert not outcomes["rail"].written
    assert all(outcomes[subsystem].written for subsystem in ("door", "acv", "shm"))
    assert all(outputs[subsystem].exists() for subsystem in ("door", "acv", "shm"))


def test_generate_all_covers_every_subsystem_in_order(monkeypatch):
    monkeypatch.setattr(generate, "generate", generate.Outcome)

    assert [outcome.subsystem for outcome in generate.generate_all()] == list(config.SUBSYSTEMS)


def test_load_predictor_reports_a_subsystem_that_has_no_module():
    with pytest.raises(ImportError):
        generate.load_predictor("nonesuch")
