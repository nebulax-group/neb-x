"""Review packages contain selected evidence, and never resurrect stale runs."""

from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
from unittest.mock import Mock
import zipfile

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.app import cache, handoff, workspace
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


def test_switching_systems_keeps_each_run_and_avoids_repeat_prediction(monkeypatch):
    reading = Mock(return_value=cache.Reading(pd.DataFrame(), [], None))
    monkeypatch.setattr(workspace.cache, "reading", reading)
    monkeypatch.setattr(workspace.cache, "_staged", lambda *args: [])
    monkeypatch.setattr(workspace.services, "review_report", lambda *args: report())
    state = {}
    door = workspace.assess("door", [upload()], state)
    workspace.assess("shm", [upload("stress.csv")], state)
    assert workspace.assess("door", [upload()], state) is door
    assert set(workspace.runs(state)) == {"door", "shm"}
    assert reading.call_count == 2
    assert workspace.runs({}) == {}  # A different browser session sees no runs.


def test_replacing_files_with_invalid_data_removes_old_report(monkeypatch):
    state = {workspace.STATE_KEY: {"door": run()}}
    monkeypatch.setattr(workspace.cache, "reading", Mock(side_effect=ValueError("wrong layout")))
    with pytest.raises(ValueError):
        workspace.assess("door", [upload(data=b"bad")], state)
    assert not workspace.runs(state)


def test_clearing_one_system_preserves_the_others():
    state = {workspace.STATE_KEY: {"door": run(), "shm": run("shm")}}
    workspace.assess("door", [], state)
    assert set(workspace.runs(state)) == {"shm"}


def test_evidence_failure_preserves_result_but_is_never_reported_clear(monkeypatch):
    monkeypatch.setattr(workspace.cache, "reading", lambda *args: cache.Reading(pd.DataFrame(), [], None))
    monkeypatch.setattr(workspace.cache, "_staged", lambda *args: [])
    monkeypatch.setattr(workspace.services, "review_report", Mock(side_effect=RuntimeError("broken")))
    result = workspace.assess("shm", [upload()], {})
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
