"""An explanation that disagrees with the prediction beside it is worse than none.

explain.py reads its numbers out of the same feature row the estimator
classified, which is what keeps the two from drifting -- so the test that
matters most here is simply that the call on every cell equals the call in the
prediction table for the same files. The rest checks that each panel is a shape
src/app/services.py documents, because the app draws whatever comes back and a
missing key surfaces as a blank card rather than as an error.
"""

import numpy as np
import pytest

from src.app import config as app_config
from src.app import services
from src.rail import config, explain, predict

PANEL_KINDS = {"verdict", "metrics", "bullet", "bars", "line", "strip"}


@pytest.fixture(scope="module")
def batch(side_i_path, side_ii_path, still_path):
    """One file of each call, explained in a single pass over the batch."""
    return [side_i_path, side_ii_path, still_path]


def panel_of(panels, kind):
    return next(panel for panel in panels if panel["kind"] == kind)


def test_every_panel_is_a_kind_the_app_knows_how_to_draw(side_i_path, checkpoint):
    panels = explain.explain([side_i_path])
    assert panels, "a fault call with no workings is a verdict nobody can check"
    assert [panel["kind"] for panel in panels] == ["verdict", "line", "metrics", "bars"]
    for panel in panels:
        assert panel["kind"] in PANEL_KINDS
        assert panel.get("subject"), panel["kind"]
        if panel["kind"] != "verdict":
            assert panel["title"] and panel["caption"]


def test_the_verdict_names_the_rail_the_model_named_and_says_what_to_do(
    side_i_path, side_ii_path, checkpoint
):
    for path, label in ((side_i_path, config.LABEL_SIDE_I), (side_ii_path, config.LABEL_SIDE_II)):
        verdict = panel_of(explain.explain([path]), "verdict")
        assert verdict["headline"] == f"Corrugation on the {label} rail"
        assert verdict["severity"] == config.SEVERITIES[label]
        assert verdict["severity"] in app_config.SEVERITY_WORDS
        assert "x louder than the other rail" in verdict["detail"]
        recommendation = verdict["recommendation"]
        assert label in recommendation["title"] and path.name in recommendation["title"]
        assert recommendation["steps"] and all("{" not in step for step in recommendation["steps"])
        assert config.RECOMMENDATION_SCOPE in recommendation["steps"]


def test_a_clear_call_names_no_rail_and_offers_the_clear_steps(still_path, checkpoint):
    verdict = panel_of(explain.explain([still_path]), "verdict")
    assert verdict["headline"] == explain.VERDICT_HEADLINE_NORMAL
    assert verdict["severity"] == config.SEVERITY_CLEAR
    assert not any(label in verdict["headline"] for label in config.SIDE_LABELS)
    assert verdict["recommendation"]["title"] == config.RECOMMENDATIONS[config.SEVERITY_CLEAR]["title"]


def test_every_cell_calls_the_file_exactly_what_the_prediction_table_calls_it(batch, checkpoint):
    """The one check that catches explain and predict drifting apart. Both are
    run over the same paths and compared row for row, in order."""
    rows = predict.predict(batch, checkpoint)
    cells = panel_of(explain.explain(batch), "strip")["cells"]
    assert [cell["title"] for cell in cells] == [path.name for path in batch]
    assert [cell["status"] for cell in cells] == list(rows[config.PREDICTION_COLUMNS[1]])
    assert [cell["state"] for cell in cells] == [
        config.SEVERITIES[call] for call in rows[config.PREDICTION_COLUMNS[1]]
    ]
    assert [cell["label"] for cell in cells] == ["01", "02", "03"]


def test_a_batch_is_drawn_whole_and_a_single_file_is_not(batch, side_i_path, checkpoint):
    """A strip of one cell is a control with nothing to choose between."""
    batched = [panel["kind"] for panel in explain.explain(batch)]
    alone = [panel["kind"] for panel in explain.explain([side_i_path])]
    assert "strip" in batched and "strip" not in alone
    assert batched.index("strip") == 1, "the batch is what the verdict leaves unsaid"


def test_a_batch_verdict_says_it_describes_only_the_most_suspected_file(batch, checkpoint):
    verdict = panel_of(explain.explain(batch), "verdict")
    assert f"Most suspected of the {len(batch)} files checked" in verdict["detail"]
    assert verdict["subject"] in {path.name for path in batch}


def test_a_stationary_file_drops_the_panels_that_need_a_wavelength(still_path, checkpoint):
    """No speed, no wavelength: the spectrum and the localisation have no x axis.
    Drawing them empty would be a chart saying nothing rather than a panel absent."""
    panels = explain.explain([still_path])
    assert [panel["kind"] for panel in panels] == ["verdict", "metrics"]
    assert panel_of(panels, "verdict")["detail"] == explain.VERDICT_STILL_DETAIL
    reading = panel_of(panels, "metrics")
    speed = next(item for item in reading["items"] if item["label"] == "Train speed")
    assert speed["value"] == "0.0 m/s" and speed["detail"] == explain.STATIONARY_DETAIL


def test_the_spectrum_is_two_matched_lists_running_left_to_right(side_i_path, checkpoint):
    """Altair joins the points in the order given, so an unsorted x doubles the
    line back over itself and the curve reads as noise."""
    line = panel_of(explain.explain([side_i_path]), "line")
    x, y = line["points"]
    assert len(x) == len(y) > 0
    assert x == sorted(x)
    assert all(np.isfinite(value) for value in x + y)
    assert min(x) >= config.WAVELENGTH_EDGES_M[0] * explain.MILLIMETRES_PER_METRE * 0.99
    assert max(x) <= config.WAVELENGTH_EDGES_M[-1] * explain.MILLIMETRES_PER_METRE * 1.01


def test_the_localisation_is_one_share_per_car_and_the_shares_add_up(side_i_path, checkpoint):
    """The app draws these on a 0-1 axis; anything else silently overflows it."""
    bars = panel_of(explain.explain([side_i_path]), "bars")
    assert len(bars["rows"]) == config.CARS
    assert [row["label"] for row in bars["rows"]] == [f"Car {n}" for n in range(1, config.CARS + 1)]
    assert all(0.0 <= row["value"] <= 1.0 for row in bars["rows"])
    assert sum(row["value"] for row in bars["rows"]) == pytest.approx(1.0)
    per_car = config.N_AXLE_BOXES // len(config.SIDE_BOXES) // config.CARS
    assert all(row["detail"] == f"{per_car} axle boxes" for row in bars["rows"])


def test_the_probability_shown_is_never_rounded_up_into_a_certainty():
    assert explain._confidence(0.994) == "99%"
    assert explain._confidence(0.995) == ">99%"
    assert explain._confidence(1.0) == ">99%"


def test_explaining_nothing_is_refused(checkpoint):
    with pytest.raises(ValueError, match="No rail input files"):
        explain.explain([])


def test_the_app_splits_rails_panels_into_one_answer_and_the_rest(batch, checkpoint):
    """split_panels is how the page decides what goes above the fold, and it
    expects exactly one verdict from any subsystem."""
    verdicts, workings = services.split_panels(explain.explain(batch))
    assert len(verdicts) == 1
    assert workings and all(panel["kind"] != "verdict" for panel in workings)
