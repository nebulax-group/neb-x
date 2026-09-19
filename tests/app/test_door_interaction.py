"""Cycle selections survive ordinary app interaction without rerunning inference."""

from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.app import cache, services
from src.door.explain import _cells


def _app():
    from io import BytesIO

    import streamlit as st

    from src.app import cache
    from src.app.ui.explain import render_panel

    other = st.checkbox("Other recording")
    hidden = st.checkbox("Hide cycles")
    upload = BytesIO(b"recording")
    upload.name = "second.csv" if other else "first.csv"
    answer = cache.reading("door", [upload])
    if not hidden:
        render_panel(answer.panels[0])


@pytest.fixture
def cycle_app(monkeypatch):
    rows = pd.DataFrame({
        "prediction": ["Normal", "Abnormal resistance", "Normal"],
        "start_time": ["10:00:00", "10:00:10", "10:00:20"],
        "end_time": ["10:00:03", "10:00:13", "10:00:23"],
    })
    bounds = pd.DataFrame({"operation": ["Open", "Close", "Open"]})
    cells = _cells(rows, bounds)
    prediction = Mock(return_value=rows)
    explanation = Mock(side_effect=lambda subsystem, inputs: [{
        "kind": "strip", "title": "Every cycle in order",
        "subject": inputs[0].name, "cells": cells,
    }])
    monkeypatch.setattr(services, "stage_uploads", lambda uploads: [Path(item.name) for item in uploads])
    monkeypatch.setattr(services, "run_prediction", prediction)
    monkeypatch.setattr(services, "explain_prediction", explanation)
    cache._staged.clear()
    cache._prediction.clear()
    cache._explanation.clear()
    yield AppTest.from_function(_app).run(), prediction, explanation
    cache._staged.clear()
    cache._prediction.clear()
    cache._explanation.clear()


def _readout(app):
    return next(item.value for item in app.markdown if 'class="nx-cycle-detail ' in item.value or 'class="nx-strip-detail"' in item.value)


def test_click_shows_full_cycle_details_and_reuses_inference(cycle_app):
    app, prediction, explanation = cycle_app
    assert not app.exception
    assert app.radio[0].value == 1  # First abnormal cycle is selected initially.
    assert "Abnormal resistance" in _readout(app)

    app.radio[0].set_value(2).run()
    assert not app.exception
    assert "Cycle 03" in _readout(app)
    assert "Opening" in _readout(app)
    assert "Normal" in _readout(app)
    assert '<dt>Start</dt><dd>10:00:20' in _readout(app)
    assert '<dt>End</dt><dd>10:00:23' in _readout(app)
    assert "nx-sev-clear" in _readout(app)
    app.run()
    assert app.radio[0].value == 2
    prediction.assert_called_once()
    explanation.assert_called_once()


def test_selection_survives_switching_away_from_the_cycle_panel(cycle_app):
    app, _, _ = cycle_app
    app.radio[0].set_value(2).run()
    app.checkbox[1].check().run()
    assert len(app.radio) == 0
    app.checkbox[1].uncheck().run()
    assert not app.exception
    assert app.radio[0].value == 2


def test_new_recording_does_not_inherit_previous_selection(cycle_app):
    app, prediction, explanation = cycle_app
    app.radio[0].set_value(2).run()
    app.checkbox[0].check().run()
    assert not app.exception
    assert app.radio[0].value == 1
    assert prediction.call_count == explanation.call_count == 2


def test_cycle_detail_is_escaped():
    def app_with_untrusted_detail():
        from src.app.ui.explain import render_panel
        render_panel({
            "kind": "strip", "title": "Cycles",
            "cells": [{"label": "01", "state": "clear", "detail": "<script>bad()</script>"}],
        })

    app = AppTest.from_function(app_with_untrusted_detail).run()
    assert not app.exception
    assert "&lt;script&gt;" in _readout(app)
    assert "<script>" not in _readout(app)


def test_native_timestamps_are_readable_with_exact_milliseconds_and_duration():
    rows = pd.DataFrame({
        "prediction": ["Abnormal resistance"],
        "start_time": ["2023-7-5-0-0-15-5"],
        "end_time": ["2023-7-5-0-0-18-765"],
    })
    original = rows.copy(deep=True)
    cell = _cells(rows, pd.DataFrame({"operation": ["Close"]}))[0]
    assert cell["fields"] == [
        {"label": "Start", "value": "00:00:15.005", "detail": "5 Jul 2023"},
        {"label": "End", "value": "00:00:18.765", "detail": "5 Jul 2023"},
        {"label": "Duration", "value": "3.760 s", "detail": "Elapsed time"},
    ]
    assert cell["state"] == "danger"
    pd.testing.assert_frame_equal(rows, original)


def test_cycle_spanning_midnight_shows_both_dates():
    rows = pd.DataFrame({
        "prediction": ["Normal"],
        "start_time": ["2023-7-5-23-59-59-900"],
        "end_time": ["2023-7-6-0-0-0-100"],
    })
    fields = _cells(rows, pd.DataFrame({"operation": ["Open"]}))[0]["fields"]
    assert fields[0]["detail"] == "5 Jul 2023"
    assert fields[1]["detail"] == "6 Jul 2023"
    assert fields[2]["value"] == "0.200 s"
