"""Next steps follow the assessed evidence and survive switching result views."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.acv import explain as acv
from src.door import explain as door
from src.shm import explain as shm


@pytest.mark.parametrize(
    "flags, expected_severity, instruction",
    [
        ([False, False, False], "clear", "monitor the next recording"),
        ([True, False, True], "caution", "arrange a door inspection"),
        ([True, True, True], "danger", "Escalate repeated resistance"),
    ],
)
def test_door_next_steps_reflect_occasional_or_sustained_resistance(
    monkeypatch, flags, expected_severity, instruction
):
    rows = pd.DataFrame({
        "prediction": [door.LABEL_ABNORMAL if flag else door.LABEL_NORMAL for flag in flags],
        "start_time": [f"start-{i}" for i in range(len(flags))],
        "end_time": [f"end-{i}" for i in range(len(flags))],
    })
    bounds = pd.DataFrame({"operation": ["Open"] * len(flags)})
    monkeypatch.setattr(door.predict, "predict", lambda inputs: rows)
    monkeypatch.setattr(door.dataset, "load_stream", lambda path: pd.DataFrame({door.COLUMN_CURRENT: [1, 2, 1]}))
    monkeypatch.setattr(door.segment, "segment_bounds", lambda stream: bounds)
    monkeypatch.setattr(door.features, "build", lambda stream: pd.DataFrame({"ratio": [1.0, 1.2, 1.0]}))

    verdict = door.explain([Path("door.csv")])[0]
    assert verdict["severity"] == expected_severity
    assert instruction in verdict["recommendation"]["title"]
    assert verdict["recommendation"]["steps"]


@pytest.mark.parametrize(
    "cars, excess, instruction",
    [
        (["03", "01"], [2.0, 0.0], "Start the ACV inspection with Car 03"),
        (["03", "01"], [-0.71, -0.728], "Check Car 03 and Car 01 together"),
        (["07"], [1.0], "Start the ACV inspection with Car 07"),
    ],
)
def test_acv_guidance_names_the_cars_and_keeps_leak_confirmation_separate(cars, excess, instruction):
    verdict = acv._verdict(Path("case.xlsx"), pd.DataFrame({
        "car_id": cars, "temperature_excess": excess,
    }))
    assert verdict["recommendation"]["title"] == instruction
    assert "confirm the cause" in " ".join(verdict["recommendation"]["steps"])


@pytest.mark.parametrize(
    "damage, expected_severity, instruction",
    [
        (0.0, "clear", "review the accumulated history"),
        (0.5, "clear", "review the accumulated history"),
        (0.51, "caution", "Prioritise an engineering review of stress.csv"),
        (1.0, "danger", "urgent structural review"),
    ],
)
def test_shm_next_steps_follow_thresholds_and_explain_recording_scope(
    monkeypatch, damage, expected_severity, instruction
):
    monkeypatch.setattr(shm, "read_stress_series", lambda path: np.array([0.0, 1.0, 0.0]))
    monkeypatch.setattr(shm, "extract_cycles", lambda series: np.array([[1.0, 0.0, 1.0]]))
    model = SimpleNamespace(exponent=2.0, predict=lambda cycles: damage)
    verdict = shm.explain([Path("stress.csv")], model=model)[0]
    assert verdict["severity"] == expected_severity
    assert instruction in verdict["recommendation"]["title"]
    assert "Check prior damage separately" in " ".join(verdict["recommendation"]["steps"])


def _assessment_app(panels):
    import pandas as pd
    from src.app.ui import assessment

    assessment.render(
        pd.DataFrame({"file_id": ["case.xlsx"], "ranked_cars": ["03|01"]}),
        "acv_predictions.csv", "ACV", panels,
    )


def test_recommendations_stay_visible_in_answer_and_details_and_escape_filenames():
    verdict = acv._verdict(Path("<script>case.xlsx"), pd.DataFrame({
        "car_id": ["03", "01"], "temperature_excess": [2.0, 0.0],
    }))
    app = AppTest.from_function(_assessment_app, args=([verdict],)).run()
    assert not app.exception
    html = "\n".join(element.value for element in app.markdown)
    assert "What to do next" in html
    assert "&lt;script&gt;case.xlsx" in html
    assert "<script>case.xlsx" not in html
    assert len(app.get("download_button")) == 1

    app.segmented_control[0].set_value("technical").run()
    assert not app.exception
    html = "\n".join(element.value for element in app.markdown)
    assert "Start the ACV inspection with Car 03" in html
    assert len(app.dataframe) == 1
    assert len(app.get("download_button")) == 1


def test_missing_explanation_does_not_invent_recommendations_or_block_download():
    app = AppTest.from_function(_assessment_app, args=([],)).run()
    assert not app.exception
    assert "What to do next" not in "\n".join(element.value for element in app.markdown)
    assert len(app.get("download_button")) == 1
