"""Rail through the caller that actually runs it, which is the app and not pytest.

src/app/services.py wraps anything predict() raises in AssessmentFailed, so an
error rail raises late reaches the page as "the assessment was interrupted" --
the app blaming itself for a file the reader could fix. That is the whole reason
validate.py exists, and it is only true if validate catches the malformed cases
before the predictor is reached. Each of those is checked here end to end.
"""

import numpy as np
import pandas as pd
import pytest

from src.app import config as app_config
from src.app import services
from src.common.config import PREDICTION_FILENAMES
from src.rail import config

SUBSYSTEM = config.SUBSYSTEM_KEY


def rail_csv(path, rows=config.SAMPLES_PER_FILE, columns=None, hole=None):
    frame = pd.DataFrame(
        np.zeros((rows, len(columns or config.EXPECTED_HEADERS))),
        columns=columns or config.EXPECTED_HEADERS,
    )
    if hole is not None:
        frame.iloc[hole] = np.nan
    frame.to_csv(path, index=False)
    return path


def kind_of(excinfo) -> str:
    return services.describe_failure(excinfo.value).kind


def test_the_app_can_find_rail_and_knows_what_to_call_its_download():
    assert services.is_available(SUBSYSTEM)
    assert services.load_explainer(SUBSYSTEM) is not None
    assert services.prediction_filename(SUBSYSTEM) == PREDICTION_FILENAMES[SUBSYSTEM]
    assert SUBSYSTEM in app_config.SUBSYSTEM_LABELS


def test_a_held_out_recording_runs_end_to_end_and_comes_back_as_submission_rows(
    held_out_paths, checkpoint
):
    rows = services.run_prediction(SUBSYSTEM, held_out_paths[:1])
    assert list(rows.columns) == list(config.PREDICTION_COLUMNS)
    assert list(rows[config.PREDICTION_COLUMNS[0]]) == [held_out_paths[0].name]
    panels = services.explain_prediction(SUBSYSTEM, held_out_paths[:1])
    verdicts, _ = services.split_panels(panels)
    assert len(verdicts) == 1


def test_a_file_from_another_system_is_a_mismatch_and_never_reaches_the_model(tmp_path):
    path = rail_csv(tmp_path / "notrail.csv", rows=3, columns=["a", "b"])
    with pytest.raises(ValueError) as caught:
        services.run_prediction(SUBSYSTEM, [path])
    assert kind_of(caught) == app_config.FAILURE_MISMATCH
    assert "does not match the rail schema" in str(caught.value)


def test_a_truncated_export_is_the_readers_problem_and_is_named_as_one(tmp_path):
    """Raised inside predict this arrives as an internal failure, which tells the
    reader nothing they can act on. validate has to reach it first."""
    path = rail_csv(tmp_path / "short.csv", rows=5)
    with pytest.raises(ValueError) as caught:
        services.run_prediction(SUBSYSTEM, [path])
    assert kind_of(caught) == app_config.FAILURE_MISMATCH
    assert "short.csv holds 5 samples" in str(caught.value)


def test_a_hole_in_a_channel_is_the_readers_problem_too(tmp_path):
    path = rail_csv(tmp_path / "holey.csv", hole=11)
    with pytest.raises(ValueError) as caught:
        services.run_prediction(SUBSYSTEM, [path])
    assert kind_of(caught) == app_config.FAILURE_MISMATCH
    assert "missing or non-finite" in str(caught.value)


def test_an_empty_file_stays_an_unreadable_failure_and_not_a_schema_one(tmp_path):
    """Nothing parsed, so nothing can be said about its columns."""
    path = tmp_path / "empty.csv"
    path.write_text("")
    with pytest.raises(pd.errors.EmptyDataError) as caught:
        services.run_prediction(SUBSYSTEM, [path])
    assert kind_of(caught) == app_config.FAILURE_UNREADABLE


def test_an_untrained_rail_reads_as_setup_missing_rather_than_as_a_bad_upload(
    tmp_path, monkeypatch, held_out_paths
):
    from src.rail import predict

    monkeypatch.setattr(predict, "CHECKPOINT_PATH", tmp_path / "absent.pkl")
    with pytest.raises(services.SubsystemUnavailable) as caught:
        services.run_prediction(SUBSYSTEM, held_out_paths[:1])
    assert kind_of(caught) == app_config.FAILURE_UNAVAILABLE


def test_a_staged_upload_is_named_without_the_directory_it_was_staged_into(tmp_path):
    """services strips its own temporary path out of whatever rail quotes back,
    and it can only do that if rail names the file and not the full path."""
    path = rail_csv(tmp_path / "Test1.csv", rows=4)
    with pytest.raises(ValueError) as caught:
        services.run_prediction(SUBSYSTEM, [path])
    failure = services.describe_failure(caught.value, [path])
    assert str(tmp_path) not in failure.reason
    assert failure.subjects[0] == "Test1.csv"
