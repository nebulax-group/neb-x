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

import numpy as np
import pandas as pd

from . import dataset, features


def _rank_worst_last(values: pd.Series) -> pd.Series:
    """Dense-rank best first, with a NaN value sent to the worst rank instead of NaN.

    na_option="bottom" gives an unusable car the worst rank instead of leaving it NaN
    (which plain .astype(int) would then raise on) - required so a car with no usable
    reading stays in the report, ranked last, rather than being dropped: a car missing
    from ranked_cars scores zero under the organisers' formula.

    rank()'s default method averages tied positions, which always lands on a whole
    number or a half - e.g. four cars tied for ranks 5-8 average to 6.5. Plain
    .astype(int) truncates, so every such .5 is silently floored (6.5 -> 6, matching
    the better-ranked group's boundary purely by luck of being even); floor(x + 0.5)
    rounds ties up instead, so a tied group lands just past the better ranks (6.5 -> 7)
    rather than appearing to overlap them.
    """
    ranks = values.rank(ascending=False, na_option="bottom")
    return np.floor(ranks + 0.5).astype(int)


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
    table["excess_rank"] = _rank_worst_last(table["temperature_excess"])
    table["duty_rank"] = _rank_worst_last(table["cooling_duty_cycle"])
    return table.sort_values("excess_rank").reset_index(drop=True)
