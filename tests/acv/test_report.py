"""The confirmation report is how a disagreement between signals becomes visible."""

from src.common import config as common_config
from src.acv import dataset, report


def test_report_covers_every_car_with_both_signals():
    frame = report.confirmation(dataset.test_case_paths()[0])
    assert len(frame) == 8
    assert list(frame.columns) == [
        "car_id", "temperature_excess", "cooling_duty_cycle",
        "excess_rank", "duty_rank",
    ]
    assert frame["excess_rank"].tolist() == sorted(frame["excess_rank"].tolist())


def test_the_top_ranked_car_is_reported_first():
    frame = report.confirmation(dataset.test_case_paths()[0])
    assert frame["car_id"].iloc[0] == "01"
    assert frame["excess_rank"].iloc[0] == 1


def test_a_car_with_no_temperature_signal_stays_in_the_report():
    """Guards the one way this subsystem can score zero: a car missing from
    ranked_cars. acv_case_04.xlsx declares eight car columns but only four carry
    usable temperature data, so temperature_excess is NaN for the rest - exactly the
    input that used to crash report.confirmation (.astype(int) on a NaN rank raises)
    and, if that ever regresses, would now silently drop a car instead.
    """
    path = common_config.TRAIN_PATHS["acv"] / "acv_case_04.xlsx"
    _, cars = dataset.load_case(path)
    frame = report.confirmation(path)

    assert set(frame["car_id"]) == set(cars)
    assert len(frame) == len(cars)

    unusable = frame[frame["temperature_excess"].isna()]
    usable = frame[frame["temperature_excess"].notna()]
    assert not unusable.empty, "this file is expected to have an unusable car"
    assert not usable.empty

    # Every NaN car must rank worse than every car with a real reading - "worst",
    # not merely "somewhere" - and none may be absent from the table.
    assert unusable["excess_rank"].min() > usable["excess_rank"].max()

    assert frame["excess_rank"].dtype.kind == "i"
