"""A failure reaches the page in the reader's terms, not the interpreter's.

The two things guarded here are the two that survive being read on screen: a staged
upload's temporary directory, which only this app knows about and nobody can act on,
and the quotes ``str`` puts round a KeyError's message. Both render as a sentence
that looks deliberate, so neither shows up as a crash anyone would investigate.
"""

import zipfile
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

from src.app import config, services


class _Upload:
    """An upload duck-typed the way services.py expects one."""

    def __init__(self, name):
        self.name = name


def test_a_staged_upload_is_named_without_the_directory_it_was_staged_into():
    staged = r"C:\Users\Someone\AppData\Local\Temp\neb-x-uploads-ab12\0f3d\Test.csv"
    failure = services.describe_failure(
        ValueError(f"Expected 1 dynamic-stress column in {staged}, found 17."),
        [_Upload("Test.csv")],
    )
    assert failure.reason == "Expected 1 dynamic-stress column in Test.csv, found 17."


def test_a_posix_staging_path_is_stripped_too():
    """The app is demonstrated on Windows and deployed on Linux."""
    failure = services.describe_failure(
        ValueError("Expected 1 dynamic-stress column in /tmp/neb-x-uploads-q/0f3d/a.csv, found 4."),
        [_Upload("a.csv")],
    )
    assert failure.reason == "Expected 1 dynamic-stress column in a.csv, found 4."


def test_a_key_error_loses_the_quotes_str_puts_round_it():
    failure = services.describe_failure(KeyError("Stream is missing the 'Datetime' column."))
    assert failure.reason == "Stream is missing the 'Datetime' column."


@pytest.mark.parametrize(
    "exc, kind",
    [
        (ValueError("No per-car columns found; the file layout is unexpected."), config.FAILURE_MISMATCH),
        (KeyError("Stream is missing the 'Datetime' column."), config.FAILURE_MISMATCH),
        (zipfile.BadZipFile("File is not a zip file"), config.FAILURE_UNREADABLE),
        (pd.errors.EmptyDataError("No columns to parse from file"), config.FAILURE_UNREADABLE),
        (services.SubsystemUnavailable("The Rail Corrugation predictor is not available yet."), config.FAILURE_UNAVAILABLE),
        (FileNotFoundError("No SHM model"), config.FAILURE_UNAVAILABLE),
        (RuntimeError("Unexpected processing problem"), config.FAILURE_INTERNAL),
        (PermissionError("Cannot write uploads"), config.FAILURE_INTERNAL),
    ],
)
def test_each_failure_is_sorted_into_the_kind_the_page_has_copy_for(exc, kind):
    assert services.describe_failure(exc).kind == kind


def test_the_file_the_reason_names_is_the_first_one_offered_to_the_reader():
    """With sixteen segments uploaded, the one that stopped the run is the one to read."""
    uploads = [_Upload(f"test{index:02d}.csv") for index in range(1, 5)] + [_Upload("Test.csv")]
    failure = services.describe_failure(
        ValueError("Expected 1 dynamic-stress column in Test.csv, found 17."), uploads
    )
    assert failure.subjects[0] == "Test.csv"
    assert set(failure.subjects) == {upload.name for upload in uploads}


@pytest.mark.parametrize("subsystem, content", [
    ("shm", "Car 01 - Indoor Average Temperature,Car 01 - ACV Control Temperature (Cooling)\n27,24\n28,24\n"),
    ("shm", "filename,damage\ntrain01.csv,0.1\n"),
    ("shm", "stress\n1\n2\n"),
    ("shm", "1\ninf\n"),
    ("shm", "1\n"),
    ("door", "1\n2\n3\n"),
    ("acv", "1\n2\n3\n"),
])
def test_wrong_recordings_are_rejected_before_loading_a_model(tmp_path, monkeypatch, subsystem, content):
    path = tmp_path / "recording.csv"
    path.write_text(content)
    loader = Mock()
    monkeypatch.setattr(services, "load_predictor", loader)
    with pytest.raises(ValueError) as caught:
        services.run_prediction(subsystem, [path])
    assert services.describe_failure(caught.value).kind == config.FAILURE_MISMATCH
    loader.assert_not_called()


def test_acv_workbook_cannot_be_used_as_shm(tmp_path):
    path = tmp_path / "acv_case.xlsx"
    pd.DataFrame({"Car 01 - Indoor Average Temperature": [27, 28],
                  "Car 01 - ACV Control Temperature (Cooling)": [24, 24]}).to_excel(path, index=False)
    with pytest.raises(ValueError, match="dynamic-stress column"):
        services.run_prediction("shm", [path])


def test_renaming_csv_to_xlsx_is_unreadable_instead_of_a_schema_failure(tmp_path):
    path = tmp_path / "recording.xlsx"
    path.write_text("1\n2\n3\n")
    with pytest.raises(zipfile.BadZipFile) as caught:
        services.run_prediction("shm", [path])
    assert services.describe_failure(caught.value).kind == config.FAILURE_UNREADABLE


def test_duplicate_names_are_rejected_before_any_upload_is_overwritten():
    with pytest.raises(ValueError, match="same filename"):
        services.stage_uploads([_Upload("test.csv"), _Upload("test.csv")])


@pytest.mark.parametrize("subsystem", ["door", "acv", "shm"])
def test_empty_recording_stays_an_unreadable_failure(tmp_path, subsystem):
    path = tmp_path / "empty.csv"
    path.write_text("")
    with pytest.raises(pd.errors.EmptyDataError) as caught:
        services.run_prediction(subsystem, [path])
    assert services.describe_failure(caught.value).kind == config.FAILURE_UNREADABLE


def test_extra_door_files_have_an_actionable_error():
    with pytest.raises(ValueError, match="exactly one.*Remove the extra files"):
        services.run_prediction("door", [Path("one.csv"), Path("two.csv")])


@pytest.mark.parametrize("subsystem, content", [
    ("shm", "-2\n0\n3\n0\n"),
    ("acv", "Car 01 - Indoor Average Temperature,Car 01 - ACV Control Temperature (Cooling),Car 02 - Indoor Average Temperature,Car 02 - ACV Control Temperature (Cooling)\n27,24,,\n28,24,,\n"),
    ("door", "Datetime,Motor current(mA),Door is opening,Door is closing\n2025-1-1-0-0-0-0,100,1,0\n2025-1-1-0-0-0-20,110,1,0\n"),
])
def test_valid_layout_reaches_predictor_without_changing_inputs(tmp_path, monkeypatch, subsystem, content):
    path = tmp_path / "OriginalName.csv"
    path.write_text(content)
    expected = pd.DataFrame({"prediction": [0.1]})
    predictor = Mock(return_value=expected)
    monkeypatch.setattr(services, "load_predictor", lambda _: predictor)
    assert services.run_prediction(subsystem, [path]) is expected
    predictor.assert_called_once_with([path])


@pytest.mark.parametrize("error, expected_kind", [
    (FileNotFoundError("Model checkpoint missing"), config.FAILURE_UNAVAILABLE),
    (ValueError("Invalid model coefficients"), config.FAILURE_INTERNAL),
    (RuntimeError("Model processing failed"), config.FAILURE_INTERNAL),
])
def test_failures_after_validation_do_not_blame_the_upload(tmp_path, monkeypatch, error, expected_kind):
    path = tmp_path / "stress.csv"
    path.write_text("-2\n0\n3\n")
    monkeypatch.setattr(services, "load_predictor", lambda _: Mock(side_effect=error))
    with pytest.raises(Exception) as caught:
        services.run_prediction("shm", [path])
    assert services.describe_failure(caught.value).kind == expected_kind


def test_failure_panel_offers_recovery_and_collapses_escaped_diagnostics(monkeypatch):
    from src.app.ui import failure

    render = Mock()
    monkeypatch.setattr(failure.st, "markdown", render)
    failure.render(services.Failure(config.FAILURE_MISMATCH, "bad <script> content", ("<file>.csv",)),
                   "shm", {"shm": True, "acv": True, "door": True})
    html = render.call_args.args[0]
    assert 'role="alert"' in html
    assert "one numeric column, no header" in html
    assert "What to do next" in html
    assert "Remove the incorrect file" in html
    assert '<details class="nx-failure-report">' in html
    assert "<summary>Diagnostic details</summary>" in html
    assert "&lt;script&gt;" in html
    assert "&lt;file&gt;.csv" in html
    assert "<script>" not in html
