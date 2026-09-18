"""The confirmation report is how a disagreement between signals becomes visible."""

from src.acv import dataset, report


def test_report_covers_every_car_with_both_signals():
    frame = report.confirmation(dataset.test_case_paths()[0])
    assert len(frame) == 8
    assert list(frame.columns) == [
        "car_id", "temperature_excess", "cooling_duty_cycle",
        "excess_rank", "duty_rank", "agrees",
    ]
    assert frame["excess_rank"].tolist() == sorted(frame["excess_rank"].tolist())


def test_the_top_ranked_car_is_reported_first():
    frame = report.confirmation(dataset.test_case_paths()[0])
    assert frame["car_id"].iloc[0] == "01"
    assert frame["excess_rank"].iloc[0] == 1
