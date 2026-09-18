"""Both ACV signals side by side, so a human can see whether they agree.

The duty cycle is physically independent of the temperature excess: one measures
whether a car holds its target, the other how hard it works to try. Agreement is
evidence for the top pick; disagreement is a reason to look closer before submitting.
"""

from pathlib import Path

import pandas as pd

from . import dataset, features


def confirmation(path: str | Path) -> pd.DataFrame:
    frame, cars = dataset.load_case(path)
    excess = features.temperature_excess(frame, cars)
    duty = features.cooling_duty_cycle(frame, cars).reindex(excess.index)

    table = pd.DataFrame(
        {
            "car_id": excess.index.astype(str),
            "temperature_excess": excess.values,
            "cooling_duty_cycle": duty.values,
        }
    )
    # temperature_excess can hold NaN for a car with no usable reading (see
    # features.temperature_excess) and that car must stay in the report, ranked last,
    # rather than being dropped - dataset.py's no-dropped-cars guarantee applies here
    # too. Plain .rank(ascending=False) leaves NaN as NaN, and .astype(int) on a NaN
    # then raises, so na_option="bottom" is used to give it the worst rank instead.
    table["excess_rank"] = table["temperature_excess"].rank(
        ascending=False, na_option="bottom"
    ).astype(int)
    table["duty_rank"] = table["cooling_duty_cycle"].rank(
        ascending=False, na_option="bottom"
    ).astype(int)
    table["agrees"] = table["excess_rank"] == table["duty_rank"]
    return table.sort_values("excess_rank").reset_index(drop=True)
