"""Review packages contain selected evidence, and never resurrect stale runs."""

from concurrent.futures import wait
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import threading
from unittest.mock import Mock
import zipfile

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.app import cache, handoff, jobs, workspace
from src.acv import handoff as acv
from src.shm import handoff as shm


def upload(name="recording.csv", data=b"1\n2\n3\n"):
    value = BytesIO(data)
    value.name = name
    return value


def report(findings=None):
    return {"recipient": "Maintenance team", "summary": "One review item.", "checked_count": 3,
            "unit": "cycles", "findings": findings if findings is not None else [{"source_file": "sample.csv", "current_ratio": 1.21}],
            "actions": ["Inspect the identified asset."], "method": "Model inference.",
            "limitations": ["Confirm the finding."],
            "chart": {"title": "Evidence", "unit": "Ratio", "rows": [{"label": "Cycle 11", "value": 1.21, "severity": "caution"}]}}


def run(subsystem="door", review=None):
    return workspace.Run(subsystem, "digest", "2026-09-19T01:00:00+00:00",
                         [{"name": "recording.csv", "sha256": "a" * 64, "bytes": 6000000}],
                         cache.Reading(pd.DataFrame({"prediction": ["Normal"]}), [], None),
                         report() if review is None else review)


def settled(subsystem, uploads, state):
    """Drive one system to an answer the way the page's own poller does."""
    outcome = workspace.assess(subsystem, uploads, state)
    while outcome.state in workspace.ON_QUEUE:
        wait([jobs.jobs(state)[subsystem].future], timeout=20)
        outcome = workspace.assess(subsystem, uploads, state)
    return outcome


def answered(monkeypatch, reading=None):
    monkeypatch.setattr(workspace.cache, "reading", reading or (lambda *args: cache.Reading(pd.DataFrame(), [], None)))
    monkeypatch.setattr(workspace.cache, "staged", lambda *args: [])
    monkeypatch.setattr(workspace.services, "review_report", lambda *args: report())


def test_switching_systems_keeps_each_run_and_avoids_repeat_prediction(monkeypatch):
    reading = Mock(return_value=cache.Reading(pd.DataFrame(), [], None))
    answered(monkeypatch, reading)
    state = {}
    door = settled("door", [upload()], state).run
    settled("shm", [upload("stress.csv")], state)
    assert settled("door", [upload()], state).run is door
    assert set(workspace.runs(state)) == {"door", "shm"}
    assert reading.call_count == 2
    assert workspace.runs({}) == {}  # A different browser session sees no runs.


def test_systems_are_worked_through_one_at_a_time_in_the_order_they_started(monkeypatch):
    began, finish, order = threading.Event(), threading.Event(), []

    def held(subsystem, *args):
        order.append(subsystem)
        began.set()
        finish.wait(20)
        return cache.Reading(pd.DataFrame(), [], None)

    answered(monkeypatch, held)
    state = {}
    workspace.assess("door", [upload()], state)
    assert began.wait(10)
    assert workspace.assess("door", [upload()], state).state == workspace.RUNNING
    assert workspace.assess("shm", [upload("stress.csv")], state).state == workspace.QUEUED
    assert order == ["door"]  # The second has not been started alongside the first.
    finish.set()
    assert settled("door", [upload()], state).state == workspace.READY
    assert settled("shm", [upload("stress.csv")], state).state == workspace.READY
    assert order == ["door", "shm"]


def test_the_board_reports_where_every_system_stands(monkeypatch):
    began, finish = threading.Event(), threading.Event()

    def held(*args):
        began.set()
        finish.wait(20)
        return cache.Reading(pd.DataFrame(), [], None)

    answered(monkeypatch, held)
    available = {"door": True, "shm": True, "acv": True, "rail": False}
    state = {}
    assert workspace.standing(available, state) == {
        "door": workspace.IDLE, "shm": workspace.IDLE, "acv": workspace.IDLE,
        "rail": "absent",
    }
    workspace.assess("door", [upload()], state)
    assert began.wait(10)
    workspace.assess("shm", [upload("stress.csv")], state)
    places = workspace.standing(available, state)
    assert (places["door"], places["shm"]) == (workspace.RUNNING, workspace.QUEUED)
    finish.set()
    settled("door", [upload()], state)
    settled("shm", [upload("stress.csv")], state)
    places = workspace.standing(available, state)
    assert (places["door"], places["shm"]) == (workspace.READY, workspace.READY)


def test_a_working_system_keeps_its_batch_when_its_uploader_reports_nothing(monkeypatch):
    finish = threading.Event()

    def held(*args):
        finish.wait(10)
        return cache.Reading(pd.DataFrame(), [], None)

    answered(monkeypatch, held)
    state = {}
    assert workspace.assess("door", [upload()], state).state in workspace.ON_QUEUE
    assert workspace.assess("door", [], state).state in workspace.ON_QUEUE
    assert jobs.pending("door", state)
    finish.set()
    assert settled("door", [upload()], state).state == workspace.READY


def test_replacing_files_with_invalid_data_removes_old_report(monkeypatch):
    state = {workspace.STATE_KEY: {"door": run()}}
    monkeypatch.setattr(workspace.cache, "reading", Mock(side_effect=ValueError("wrong layout")))
    outcome = settled("door", [upload(data=b"bad")], state)
    assert outcome.state == workspace.FAILED
    assert isinstance(outcome.error, ValueError)
    assert not workspace.runs(state)


def test_clearing_a_system_resets_everything_the_session_held_about_it(monkeypatch):
    answered(monkeypatch)
    state = {"nx_panel_index-Door": 3, "nx_result_view-Door": "technical"}
    assert settled("door", [upload()], state).state == workspace.READY

    workspace.reset("door", state)

    assert not workspace.runs(state)
    assert not jobs.jobs(state)
    assert state["nx_upload_generation"]["door"] == 1
    assert "nx_panel_index-Door" not in state and "nx_result_view-Door" not in state
    assert workspace.standing({"door": True}, state) == {"door": workspace.IDLE}


def test_a_system_runs_again_after_being_cleared(monkeypatch):
    reading = Mock(return_value=cache.Reading(pd.DataFrame(), [], None))
    answered(monkeypatch, reading)
    state = {}
    for round_number in range(3):
        assert settled("door", [upload(data=b"%d" % round_number)], state).state == workspace.READY
        assert set(workspace.runs(state)) == {"door"}
        workspace.reset("door", state)
        assert not workspace.runs(state)
    assert reading.call_count == 3  # A fresh batch each time, never a replayed one.


def test_clearing_one_system_leaves_a_shared_batch_readable_for_the_other(monkeypatch):
    answered(monkeypatch)
    state = {}
    settled("door", [upload()], state)
    settled("shm", [upload()], state)
    forgotten = []
    monkeypatch.setattr(workspace.cache, "forget", forgotten.append)
    workspace.reset("door", state)
    assert not forgotten  # SHM is still holding the same files.
    workspace.reset("shm", state)
    assert len(forgotten) == 1


def test_a_system_that_finished_while_you_were_elsewhere_reaches_the_handoff(monkeypatch):
    finish = threading.Event()

    def held(*args):
        finish.wait(20)
        return cache.Reading(pd.DataFrame(), [], None)

    answered(monkeypatch, held)
    state = {}
    assert workspace.assess("shm", [upload("stress.csv")], state).state in workspace.ON_QUEUE
    finish.set()
    wait([jobs.jobs(state)["shm"].future], timeout=20)
    # The reader is on another system, so nothing asks SHM for its answer again.
    assert not workspace.runs(state)
    workspace.collect(state)
    assert set(workspace.runs(state)) == {"shm"}


def test_a_failed_run_is_never_collected_into_the_handoff(monkeypatch):
    monkeypatch.setattr(workspace.cache, "reading", Mock(side_effect=ValueError("wrong layout")))
    state = {}
    assert settled("door", [upload(data=b"bad")], state).state == workspace.FAILED
    workspace.collect(state)
    assert not workspace.runs(state)


def test_a_failed_batch_shows_on_the_board_and_is_reported_once(monkeypatch):
    reading = Mock(side_effect=ValueError("wrong layout"))
    monkeypatch.setattr(workspace.cache, "reading", reading)
    state, files = {}, [upload(data=b"bad")]
    assert settled("door", files, state).state == workspace.FAILED
    assert settled("door", files, state).state == workspace.FAILED
    assert reading.call_count == 1
    assert workspace.standing({"door": True}, state) == {"door": workspace.FAILED}


def test_clearing_one_system_preserves_the_others():
    state = {workspace.STATE_KEY: {"door": run(), "shm": run("shm")}}
    workspace.assess("door", [], state)
    assert set(workspace.runs(state)) == {"shm"}


def test_evidence_failure_preserves_result_but_is_never_reported_clear(monkeypatch):
    monkeypatch.setattr(workspace.cache, "reading", lambda *args: cache.Reading(pd.DataFrame(), [], None))
    monkeypatch.setattr(workspace.cache, "staged", lambda *args: [])
    monkeypatch.setattr(workspace.services, "review_report", Mock(side_effect=RuntimeError("broken")))
    result = settled("shm", [upload()], {}).run
    assert result.report is None
    name, payload = handoff.build({"shm": result})
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        text = archive.read(name[:-4] + "/Summary.txt").decode()
        assert "evidence is incomplete" in text
        assert "Do not interpret this as no findings" in text


def test_packet_has_neat_folders_charts_traceability_and_no_sensor_or_model_files():
    reports = {key: run(key) for key in ("door", "acv", "shm")}
    name, payload = handoff.build(reports, "Depot A / WO-123", "Reviewer", "Check source identity", datetime(2026, 9, 19, tzinfo=timezone.utc))
    root = name[:-4]
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        assert set(archive.namelist()) == {
            f"{root}/{file}" for file in ("Summary.txt", "Report.html", "manifest.json")
        } | {f"{root}/{system}/{file}" for system in reports for file in ("README.txt", "findings.csv", "evidence-01.svg")}
        manifest = json.loads(archive.read(root + "/manifest.json"))
        assert manifest["reference"] == "Depot A / WO-123"
        assert manifest["systems"]["door"]["sources"][0]["sha256"] == "a" * 64
        html = archive.read(root + "/Report.html").decode()
        assert "<svg" in html and "Suggested recipient" in html
        assert "not an LTA approval" in html
        assert "Rail Corrugation" in html
        assert "6000000" not in archive.read(root + "/door/findings.csv").decode()
    assert len(payload) < 20000


def test_clear_report_has_a_summary_but_no_findings_csv_or_chart():
    clear = shm.build([], pd.DataFrame({"file_id": ["test01.csv"], "prediction": [0.03]}), [])
    name, payload = handoff.build({"shm": run("shm", clear)})
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        assert not any(path.endswith((".csv", ".svg")) for path in archive.namelist())
        text = archive.read(name[:-4] + "/shm/README.txt").decode()
        assert "0 of 1" in text and "Prior accumulated damage is unknown" in text


def test_shm_review_selection_is_per_file_and_matches_existing_boundaries():
    frame = pd.DataFrame({"file_id": ["a", "b", "c", "d"], "prediction": [0.03, 0.5, 0.51, 1.0]})
    review = shm.build([], frame, [])
    assert [row["source_file"] for row in review["findings"]] == ["c", "d"]
    assert [row["priority"] for row in review["findings"]] == ["caution", "danger"]


def test_acv_close_ranking_includes_runner_up_even_when_below_target(monkeypatch):
    monkeypatch.setattr(acv.dataset, "load_case", lambda path: (pd.DataFrame(), {}))
    monkeypatch.setattr(acv.features, "temperature_excess", lambda *args: pd.Series({"01": -0.71, "03": -0.728, "07": -1.2}))
    frame = pd.DataFrame({"file_id": ["case.xlsx"], "ranked_cars": ["01|03|07"]})
    review = acv.build([Path("case.xlsx")], frame, [])
    assert [row["car_id"] for row in review["findings"]] == ["01", "03"]
    assert all("unconfirmed" in row["status"] for row in review["findings"])
    assert all(row["value"] < 0 for row in review["chart"]["rows"])
    assert "<svg" in handoff.chart_svg(review["chart"], review["chart"]["rows"])


def test_packet_escapes_notes_and_spreadsheet_formula_filenames():
    review = report([{"source_file": "=cmd.csv", "value": 1.2}])
    name, payload = handoff.build({"door": run(review=review)}, notes="<script>alert(1)</script>")
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        assert "<script>" not in archive.read(name[:-4] + "/Report.html").decode()
        assert "'=cmd.csv" in archive.read(name[:-4] + "/door/findings.csv").decode()


def _views_app():
    import pandas as pd
    import streamlit as st
    from src.app.ui import assessment
    system = st.radio("System", ["Door", "SHM"])
    assessment.render(pd.DataFrame({"prediction": [1]}), "unused.csv", system, [])


def test_each_window_remembers_its_own_assessment_view():
    app = AppTest.from_function(_views_app).run()
    app.segmented_control[0].set_value("technical").run()
    app.radio[0].set_value("SHM").run()
    assert app.segmented_control[0].value == "simple"
    app.radio[0].set_value("Door").run()
    assert app.segmented_control[0].value == "technical"
    assert not app.exception
