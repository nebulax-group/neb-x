"""Both ACV signals side by side, for a human to inspect before submitting.

cooling_duty_cycle was included as an independent check on the theory that a leaking
car, unable to hold its setpoint, runs its compressor longer than a healthy one.
Measured across all six case files (the five reference cases plus the held-out file),
it does not bear that out: duty cycle spans only 0.001-0.04 between the eight cars in
every single file - every car in a case runs at essentially the same duty cycle. An
exact-rank-agreement check built on that signal was false for the top-ranked car in
all six files, including the five reference cases where that car is the known-correct
answer, which shows the flatness rather than any real disagreement.

Both raw signals and both ranks are still shown, so a reader can see the flatness
themselves - and so a future file with real duty-cycle separation would be visible
too - but no agreement/disagreement verdict is computed from them.
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
    return table.sort_values("excess_rank").reset_index(drop=True)
