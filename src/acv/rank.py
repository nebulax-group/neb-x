"""Turn per-car scores into the ranked_cars field."""

import pandas as pd

from . import config


def rank_cars(scores: pd.Series) -> list[str]:
    """Car ids from most to least likely faulty. Ties break by car id, deterministically."""
    ordered = scores.sort_index().sort_values(ascending=False, kind="stable")
    return [str(car_id) for car_id in ordered.index]


def to_ranked_string(order: list[str]) -> str:
    if len(order) != len(set(order)):
        raise ValueError(f"Ranking repeats a car: {order}")
    return config.RANKED_CARS_SEPARATOR.join(order)
