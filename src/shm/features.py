"""Turn a dynamic-stress history into fatigue cycles. Arrays in, arrays out, no IO.

Fatigue damage is a property of closed stress cycles, not of samples, so the raw
history has to be reduced before Miner's rule means anything. Rainflow counting
(ASTM E1049) is the standard way to do that, and per the Info Kit §1.3 it is how
the reference damage values in this dataset were produced.

Nothing here knows about files, the training set, or the fitted S-N constants:
``damage_sum`` takes the exponent as an argument so that choosing it stays the
model's job.
"""

import numpy as np

from .config import CYCLE_AMPLITUDE, CYCLE_COLUMNS, CYCLE_COUNT

_FULL_CYCLE = 1.0
_HALF_CYCLE = 0.5


def _as_series(series: np.ndarray) -> np.ndarray:
    values = np.asarray(series, dtype=float)
    if values.ndim != 1:
        raise ValueError(f"Expected a 1-D stress series, got shape {values.shape}.")
    if values.size < 2:
        raise ValueError("A stress series needs at least two samples to have a cycle.")
    if not np.isfinite(values).all():
        raise ValueError("Stress series contains non-finite values.")
    return values


def reversals(series: np.ndarray) -> np.ndarray:
    """Turning points only — peaks and valleys, with runs and plateaus dropped.

    Samples between two turning points close no cycle, so discarding them changes
    no result and is what makes the counting below tractable on a 581,120-sample
    file. The first and last samples are always kept: they bound the residue that
    ASTM counts as half cycles.
    """
    values = _as_series(series)

    # Equal neighbours leave a zero slope, which has no sign and would hide a turn.
    keep = np.ones(values.size, dtype=bool)
    keep[1:] = values[1:] != values[:-1]
    compact = values[keep]
    if compact.size < 3:
        return compact

    slope = np.sign(np.diff(compact))
    turns = np.flatnonzero(slope[1:] != slope[:-1]) + 1
    return np.concatenate(([compact[0]], compact[turns], [compact[-1]]))


def extract_cycles(series: np.ndarray) -> np.ndarray:
    """Rainflow cycles, one row each: (amplitude, mean, count).

    The three-point stack rule of ASTM E1049. A cycle closes when the newest
    range reaches back over the one before it; the enclosed pair is counted and
    removed, and whatever is still on the stack at the end is counted as half
    cycles, which is how the standard handles a history that does not return to
    where it started.

    Amplitude is half the stress range, matching the sigma_a of the S-N curve.
    """
    turns = reversals(series)
    if turns.size < 2:
        return np.empty((0, CYCLE_COLUMNS))

    cycles: list[tuple[float, float, float]] = []
    stack: list[float] = []

    for point in turns:
        stack.append(float(point))
        while len(stack) >= 3:
            first, middle, last = stack[-3], stack[-2], stack[-1]
            enclosed = abs(middle - first)
            if abs(last - middle) < enclosed:
                break
            amplitude = enclosed / 2.0
            mean = (first + middle) / 2.0
            if len(stack) == 3:
                # The oldest point has nothing before it to pair with, so its range
                # is only ever seen once and counts as half.
                cycles.append((amplitude, mean, _HALF_CYCLE))
                stack.pop(0)
            else:
                cycles.append((amplitude, mean, _FULL_CYCLE))
                del stack[-3:-1]

    for first, second in zip(stack, stack[1:]):
        cycles.append((abs(second - first) / 2.0, (first + second) / 2.0, _HALF_CYCLE))

    if not cycles:
        return np.empty((0, CYCLE_COLUMNS))
    return np.array(cycles, dtype=float)


def cycle_damage(cycles: np.ndarray, exponent: float) -> np.ndarray:
    """Each cycle's own n_i * sigma_i^m, in the order the cycles were counted.

    Separate from ``damage_sum`` because the total hides what produced it. Raising
    amplitude to a power near five spreads these terms over many orders of
    magnitude, so a handful of cycles account for almost all of a file's damage,
    and being able to point at them is the difference between a number and an
    explanation.
    """
    if exponent <= 0:
        raise ValueError(f"S-N exponent must be positive, got {exponent}.")
    if cycles.size == 0:
        return np.empty(0, dtype=float)
    if cycles.ndim != 2 or cycles.shape[1] != CYCLE_COLUMNS:
        raise ValueError(f"Expected cycles with {CYCLE_COLUMNS} columns, got {cycles.shape}.")

    return cycles[:, CYCLE_COUNT] * cycles[:, CYCLE_AMPLITUDE] ** exponent


def damage_sum(cycles: np.ndarray, exponent: float) -> float:
    """Sum of n_i * sigma_i^m over the cycles — Miner's rule with C left out.

    Total damage is ``D = sum(n_i / N_i)`` and ``N_i = C / sigma_i^m``, so
    ``D = damage_sum(cycles, m) / C``. Dividing by C is the model's job; this
    value depends only on the data and the exponent.
    """
    return float(cycle_damage(cycles, exponent).sum())
