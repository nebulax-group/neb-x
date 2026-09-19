"""The review folder a depot receives, and the one value that must never be NaN.

src/app/handoff.py refuses a non-finite bar, and one rejected row loses the whole
rail report to "review evidence is incomplete" -- which reads as the app being
broken rather than as rail having found nothing. A stationary recording has no
ripple spacing to quote, so that case is forced here rather than waited for.

The rest of this file is the shape src/app/handoff.py reads: csv.DictWriter takes
its column names from the first record and would raise on any later row that
disagrees, and every finding has to survive being opened in a spreadsheet.
"""

import math

import numpy as np
import pytest

from src.rail import config, explain, handoff, predict

CONTRACT = {
    "recipient", "summary", "checked_count", "unit",
    "findings", "actions", "method", "limitations", "chart",
}


class _Stub:
    """An estimator that calls everything the same thing, to force a rare path."""

    def __init__(self, called):
        self.classes_ = np.array(config.LABELS)
        self._column = list(config.LABELS).index(called)

    def predict_proba(self, matrix):
        probabilities = np.full((len(matrix), len(config.LABELS)), 0.01)
        probabilities[:, self._column] = 0.98
        return probabilities


@pytest.fixture(scope="module")
def faults(side_i_path, side_ii_path, still_path, train_dir, checkpoint):
    """One of each call, so the report has findings and a clear file to ignore."""
    inputs = [side_i_path, side_ii_path, still_path, train_dir / "Train1.csv"]
    frame = predict.predict(inputs, checkpoint)
    return inputs, frame, handoff.build(inputs, frame, explain.explain(inputs))


def test_the_report_carries_every_field_the_packager_reads(faults):
    _, frame, report = faults
    assert set(report) == CONTRACT
    assert report["recipient"] and report["method"] and report["summary"]
    assert report["checked_count"] == len(frame)
    assert report["unit"] == "recordings"
    assert len(report["limitations"]) >= 3
    assert isinstance(report["limitations"], list)


def test_a_finding_is_a_named_rail_and_nothing_else_is(faults):
    """Normal recordings are not findings, and no fault call is left out of the
    list -- an absent row reads as the track being sound."""
    inputs, frame, report = faults
    called = list(frame[config.PREDICTION_COLUMNS[1]])
    flagged = [
        path.name for path, call in zip(inputs, called) if call in config.SIDE_LABELS
    ]
    assert [row["source_file"] for row in report["findings"]] == flagged
    assert {row["rail"] for row in report["findings"]} <= set(config.SIDE_LABELS)
    assert all(row["priority"] == config.SEVERITY_CAUTION for row in report["findings"])
    assert f"{len(flagged)} of {len(frame)} recordings" in report["summary"]


def test_every_finding_has_the_same_columns_as_the_first(faults):
    """csv.DictWriter takes its fieldnames from records[0] and raises on a row
    that carries a key those do not name."""
    _, _, report = faults
    columns = [set(row) for row in report["findings"]]
    assert columns and all(row == columns[0] for row in columns)


def test_no_bar_is_non_finite_and_each_carries_what_the_chart_needs(faults):
    _, _, report = faults
    rows = report["chart"]["rows"]
    assert rows, "a report with findings and no evidence chart is half a report"
    for row in rows:
        assert set(row) == {"label", "value", "severity"}
        assert math.isfinite(row["value"]), row
        assert row["value"] > 1.0, "a flagged rail is louder than its opposite number"
        # chart_svg paints danger red and everything else amber. Rail names a rail,
        # not a depth, so it has no danger to paint.
        assert row["severity"] == config.SEVERITY_CAUTION
    assert report["chart"]["title"] and report["chart"]["unit"]


def test_a_probability_is_never_printed_as_a_certainty(faults):
    """The same rule explain.py holds to. A bare 1.0 in a column a depot reads is
    the claim that decision exists to avoid making."""
    _, _, report = faults
    shown = {row["model_probability"] for row in report["findings"]}
    assert shown and all(isinstance(value, str) for value in shown)
    assert not any(value.startswith("1.0") for value in shown)
    assert all(value == ">99%" or value.endswith("%") for value in shown)


def test_the_actions_are_rail_and_file_filled_in_and_end_with_the_scope(faults):
    inputs, _, report = faults
    actions = report["actions"]
    assert all("{" not in action for action in actions)
    assert len(set(actions)) == len(actions), "the same step twice reads as two jobs"
    assert actions[-1] == config.RECOMMENDATION_SCOPE
    assert any("Side I" in action for action in actions)


def test_a_stationary_recording_says_so_rather_than_being_counted_clear(faults):
    _, frame, report = faults
    assert f"1 of the {len(frame)} recorded a stationary train" in report["summary"]
    assert any("stationary" in limitation for limitation in report["limitations"])


def test_a_fault_called_on_a_stationary_file_is_listed_without_a_margin(
    still_path, checkpoint, monkeypatch
):
    """The NaN path, forced. Ripple spacing needs speed, so a fault call on a
    stopped train has no margin to quote -- and quoting NaN would cost the whole
    rail report, not just this row."""
    stub = {**checkpoint, "estimator": _Stub(config.LABEL_SIDE_I)}
    monkeypatch.setattr(handoff, "load_checkpoint", lambda: stub)
    frame = predict.predict([still_path], checkpoint)

    report = handoff.build([still_path], frame, [])
    assert len(report["findings"]) == 1, "a fault call must reach the list either way"
    finding = report["findings"][0]
    assert finding["rail"] == config.LABEL_SIDE_I
    assert finding["ripple_spacing"] == finding["times_louder"] == handoff.NO_MARGIN
    assert report["chart"]["rows"] == [], "no speed, no bar"


def test_a_batch_with_nothing_wrong_offers_the_clear_steps_and_no_chart(
    train_dir, checkpoint, monkeypatch
):
    stub = {**checkpoint, "estimator": _Stub(config.LABEL_NORMAL)}
    monkeypatch.setattr(handoff, "load_checkpoint", lambda: stub)
    inputs = [train_dir / "Train1.csv"]
    frame = predict.predict(inputs, checkpoint)

    report = handoff.build(inputs, frame, [])
    assert report["findings"] == [] and report["chart"]["rows"] == []
    clear = config.RECOMMENDATIONS[config.SEVERITY_CLEAR]
    assert report["actions"] == [clear["title"], *clear["steps"], config.RECOMMENDATION_SCOPE]
    assert report["summary"].startswith(f"0 of {len(frame)} recordings")
