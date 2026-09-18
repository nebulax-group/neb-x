"""Per-car signals from one case file. No IO, no model.

A leaking car has reduced cooling capacity, so it cannot hold its own setpoint and
runs its compressor longer. Both signals are computed against each car's OWN target,
so a car with a different setpoint is not penalised for it.
"""

import pandas as pd

from . import config, dataset


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def temperature_excess(frame: pd.DataFrame, cars: dict) -> pd.Series:
    """Mean degrees each car sits above its own cooling setpoint."""
    values = {}
    for car_id, params in sorted(cars.items()):
        indoor = _numeric(frame, dataset.resolve(params, config.INDOOR_TEMPERATURE_CANDIDATES))
        setpoint = _numeric(frame, dataset.resolve(params, config.COOLING_SETPOINT_CANDIDATES))
        excess = (indoor - setpoint).mean()
        if pd.notna(excess):
            values[car_id] = float(excess)
    if not values:
        raise ValueError("No car produced a usable temperature signal.")
    return pd.Series(values)


def cooling_duty_cycle(frame: pd.DataFrame, cars: dict) -> pd.Series:
    """Fraction of samples in which each car is actively cooling.

    Reported alongside temperature_excess as an independent confirmation. It is
    deliberately NOT averaged into the ranking: with five reference cases, a second
    signal is worth more as a disagreement alarm than as a vote.
    """
    values = {}
    for car_id, params in sorted(cars.items()):
        modes = frame[dataset.resolve(params, config.RUNNING_MODE_CANDIDATES)]
        values[car_id] = float(modes.isin(config.COOLING_MODES).mean())
    return pd.Series(values)
