"""The S-N curve behind Miner's rule: choose the exponent m and coefficient C.

Cumulative damage is ``D = S(m) / C``, where ``S(m) = sum(n_i * sigma_i^m)``
comes from ``features.damage_sum``. The whole model is therefore two numbers
shared by every file, which is why it is fitted rather than learned and why it
cannot overfit 64 training files.

Both are chosen to minimise MAPE, the metric this subsystem is scored on.
Fitting least squares instead would chase the large-damage files and leave the
small ones — which MAPE weights equally — badly wrong.

No IO and no orchestration: cycles and labels in, a ``DamageModel`` out.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .config import (
    EXPONENT_COARSE_STEP,
    EXPONENT_FINE_STEP,
    EXPONENT_MAX,
    EXPONENT_MIN,
    MODEL_COEFFICIENT_KEY,
    MODEL_EXPONENT_KEY,
)
from .features import damage_sum


@dataclass(frozen=True)
class DamageModel:
    """A fitted S-N curve, ``sigma^exponent * N = coefficient``."""

    exponent: float
    coefficient: float

    def __post_init__(self) -> None:
        if not self.exponent > 0:
            raise ValueError(f"S-N exponent must be positive, got {self.exponent}.")
        if not self.coefficient > 0:
            raise ValueError(f"S-N coefficient must be positive, got {self.coefficient}.")

    def predict(self, cycles: np.ndarray) -> float:
        """Cumulative damage for one file's rainflow cycles."""
        return damage_sum(cycles, self.exponent) / self.coefficient

    def as_dict(self) -> dict[str, float]:
        return {
            MODEL_EXPONENT_KEY: float(self.exponent),
            MODEL_COEFFICIENT_KEY: float(self.coefficient),
        }

    @classmethod
    def from_dict(cls, values: dict[str, float]) -> "DamageModel":
        missing = [
            key
            for key in (MODEL_EXPONENT_KEY, MODEL_COEFFICIENT_KEY)
            if key not in values
        ]
        if missing:
            raise ValueError(f"Checkpoint is missing {missing}; found {list(values)}.")
        return cls(
            exponent=float(values[MODEL_EXPONENT_KEY]),
            coefficient=float(values[MODEL_COEFFICIENT_KEY]),
        )


def mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Mean absolute percentage error as a fraction, not a percentage."""
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    if actual.shape != predicted.shape:
        raise ValueError(f"Shape mismatch: {actual.shape} against {predicted.shape}.")
    if actual.size == 0:
        raise ValueError("MAPE is undefined with no samples.")
    if not np.all(actual > 0):
        raise ValueError("MAPE is undefined where the true damage is zero.")
    return float(np.mean(np.abs(1.0 - predicted / actual)))


def _grid(low: float, high: float, step: float) -> np.ndarray:
    # linspace over a counted number of points rather than arange: arange with a
    # float step drops or duplicates the endpoint depending on rounding.
    count = int(round((high - low) / step)) + 1
    return np.round(np.linspace(low, high, count), 10)


def coarse_grid() -> np.ndarray:
    """Exponents to scan first, spanning the whole plausible range."""
    return _grid(EXPONENT_MIN, EXPONENT_MAX, EXPONENT_COARSE_STEP)


def fine_grid(centre: float) -> np.ndarray:
    """Exponents within one coarse step of ``centre``, for the second pass."""
    low = max(EXPONENT_MIN, centre - EXPONENT_COARSE_STEP)
    high = min(EXPONENT_MAX, centre + EXPONENT_COARSE_STEP)
    return _grid(low, high, EXPONENT_FINE_STEP)


def damage_sums(
    cycles_by_file: Sequence[np.ndarray], exponents: np.ndarray
) -> np.ndarray:
    """``S(m)`` for every file against every exponent, as ``(files, exponents)``.

    The only expensive call in this module, and the reason it exists separately
    from ``fit``: cross-validation refits the two parameters many times over the
    same cycles, and a cached matrix makes each of those refits free.
    """
    exponents = np.asarray(exponents, dtype=float)
    if exponents.ndim != 1 or exponents.size == 0:
        raise ValueError(f"Expected a non-empty 1-D exponent grid, got {exponents.shape}.")
    if not cycles_by_file:
        raise ValueError("No files to fit; expected at least one array of cycles.")

    sums = np.empty((len(cycles_by_file), exponents.size), dtype=float)
    for row, cycles in enumerate(cycles_by_file):
        for column, exponent in enumerate(exponents):
            sums[row, column] = damage_sum(cycles, float(exponent))
    return sums


def _best_coefficient(sums: np.ndarray, damages: np.ndarray) -> float:
    """The C minimising MAPE for one fixed exponent.

    With ``r_i = S_i / D_i`` the error is ``mean|1 - r_i / C|``, which is convex
    and piecewise linear in ``1 / C`` with a breakpoint at each ``r_i``. Its
    minimum therefore sits exactly on one of them, so scanning the candidates is
    the exact optimum and no solver is involved.
    """
    ratios = sums / damages
    candidates = ratios[ratios > 0]
    if candidates.size == 0:
        raise ValueError("Every file has zero damage sum; the exponent grid cannot be fitted.")
    errors = np.abs(1.0 - ratios[None, :] / candidates[:, None]).mean(axis=1)
    return float(candidates[int(np.argmin(errors))])


def fit(sums: np.ndarray, exponents: np.ndarray, damages: np.ndarray) -> DamageModel:
    """Pick the (exponent, coefficient) pair with the lowest MAPE on these files.

    ``sums`` is a matrix from ``damage_sums`` and ``exponents`` its columns, so
    fitting a fold means passing the rows of that fold and nothing is recomputed.
    """
    sums = np.asarray(sums, dtype=float)
    exponents = np.asarray(exponents, dtype=float)
    damages = np.asarray(damages, dtype=float)

    if sums.ndim != 2:
        raise ValueError(f"Expected a (files, exponents) matrix, got shape {sums.shape}.")
    if sums.shape != (damages.size, exponents.size):
        raise ValueError(
            f"Matrix shape {sums.shape} does not match {damages.size} labels "
            f"and {exponents.size} exponents."
        )
    if not np.all(damages > 0):
        raise ValueError("Training damages must all be positive to fit against MAPE.")

    best_error = np.inf
    best: DamageModel | None = None
    for column, exponent in enumerate(exponents):
        coefficient = _best_coefficient(sums[:, column], damages)
        error = mape(damages, sums[:, column] / coefficient)
        if error < best_error:
            best_error = error
            best = DamageModel(exponent=float(exponent), coefficient=coefficient)

    if best is None:
        raise ValueError("The exponent grid was empty.")
    return best


def predict_all(
    model: DamageModel, cycles_by_file: Sequence[np.ndarray]
) -> np.ndarray:
    """Damage for a list of files, in the order given."""
    return np.array([model.predict(cycles) for cycles in cycles_by_file], dtype=float)
