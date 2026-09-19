"""Parameter names and car ids vary between files; parsing must not assume either."""

import pandas as pd
import pytest

from src.common import config as common_config
from src.acv import config, dataset


def test_car_ids_stay_strings_with_their_leading_zero():
    labels = dataset.load_labels()
    assert list(labels[config.LABEL_CAR_COLUMN]) == ["01", "02", "03", "01", "04", "06"]
    assert labels[config.LABEL_CAR_COLUMN].map(type).eq(str).all()


def test_the_car_model_column_is_not_mistaken_for_a_car():
    frame = pd.DataFrame(
        columns=["Car model", "Train number", "Time", "Car 01 - Indoor Average Temperature"]
    )
    cars = dataset.car_columns(frame)
    assert set(cars) == {"01"}


def test_every_same_schema_case_exposes_eight_cars():
    for path in dataset.validation_case_paths():
        _, cars = dataset.load_case(path)
        assert len(cars) == 8, path.name


def test_case_06_parameter_alias_resolves():
    """Case 06 says 'Outside Temperature Sensor Reading' where others say 'Outdoor...'."""
    path = common_config.TRAIN_PATHS["acv"] / "acv_case_06.xlsx"
    _, cars = dataset.load_case(path)
    params = cars["01"]
    assert dataset.resolve(params, config.INDOOR_TEMPERATURE_CANDIDATES)
    assert dataset.resolve(params, config.COOLING_SETPOINT_CANDIDATES)


def test_resolve_raises_when_no_candidate_matches():
    with pytest.raises(KeyError, match="none of"):
        dataset.resolve({"Something Else": "col"}, ("Nothing Like It",))


def test_the_odd_schema_case_is_excluded_from_validation():
    names = {p.name for p in dataset.validation_case_paths()}
    assert "acv_case_04.xlsx" not in names
    assert len(names) == 5
