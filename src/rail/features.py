"""One recording -> one fixed-length feature vector. No IO, no model, no fitting.

Cross-side log-ratios are the main signal, aggregated across a side by max and
p90 rather than a robust statistic, with bands in wavelength alongside bands in
Hz. Why each of those, and the measurements behind them, are in
.claude/memory/rail-plan.md.
"""

from functools import partial

import numpy as np
from scipy.signal import welch

from src.rail import config
from src.rail.dataset import Recording
from src.rail.speed import estimate_speed

VIBRATION, SHOCK = config.CHANNEL_NAMES

# Every aggregate a side could be summarised by; config.AGGREGATES picks which
# are built. The median stays catalogued because it is what the per-box context
# would be measured with if that question is ever reopened -- see its entry in
# config for why it is not currently one of them.
_AGGREGATE_FUNCTIONS = {
    "max": np.max,
    f"p{config.AGGREGATE_PERCENTILE}": partial(np.percentile, q=config.AGGREGATE_PERCENTILE),
    "median": np.median,
}
_AGGREGATES = tuple(_AGGREGATE_FUNCTIONS[name] for name in config.AGGREGATES)

_SIDE_NAMES = tuple(label.lower().replace(" ", "_") for label in config.SIDE_LABELS)
_SIDE_INDEX = tuple(np.fromiter(boxes, dtype=int) for boxes in config.SIDE_BOXES)


def _edge_pairs(edges: tuple[float, ...]) -> tuple[tuple[float, float], ...]:
    return tuple(zip(edges, edges[1:]))


_HZ_BANDS = _edge_pairs(config.HZ_BAND_EDGES)
_WAVELENGTH_BANDS = _edge_pairs(config.WAVELENGTH_EDGES_M)

_HZ_BAND_NAMES = tuple(f"hz{low:g}_{high:g}" for low, high in _HZ_BANDS)
WAVELENGTH_BAND_NAMES = tuple(  # millimetres, exact for every edge we use
    f"lam{round(low * 1000)}_{round(high * 1000)}" for low, high in _WAVELENGTH_BANDS
)
_SCALAR_NAMES = ("rms", "kurtosis", "crest", "centroid", "peak_hz")

# Per axle box, in the order quantities() stacks them. The wavelength names are
# public alongside so explain.py can find those rows by name rather than by an
# offset that a reordering here would silently invalidate.
QUANTITY_NAMES = _HZ_BAND_NAMES + WAVELENGTH_BAND_NAMES + _SCALAR_NAMES


def _channel_feature_names(channel: str) -> tuple[str, ...]:
    per_side = tuple(
        f"{channel}_{side}_{aggregate}_{quantity}"
        for side in _SIDE_NAMES
        for aggregate in config.AGGREGATES
        for quantity in QUANTITY_NAMES
    )
    contrast = tuple(
        f"{channel}_contrast_{aggregate}_{quantity}"
        for aggregate in config.AGGREGATES
        for quantity in QUANTITY_NAMES
    )
    return per_side + contrast


FEATURE_NAMES = tuple(
    name for channel in config.CHANNEL_NAMES for name in _channel_feature_names(channel)
)


def _band_energy(
    psd: np.ndarray, frequencies: np.ndarray, low_hz: float, high_hz: float
) -> np.ndarray:
    """Integrate the PSD of every box over [low_hz, high_hz), or NaN if it is empty.

    A band narrower than Welch's bin spacing catches no bin at all -- the longest
    wavelength band does this below ~1.8 m/s. Returning zero there would claim
    both rails measured the same thing exactly, which is a stronger statement
    than the data supports and one only slow files can make. Same argument as the
    stationary branch in quantities().
    """
    inside = (frequencies >= low_hz) & (frequencies < high_hz)
    if not inside.any():
        return np.full(psd.shape[1], np.nan)
    resolution = frequencies[1] - frequencies[0]
    return psd[inside].sum(axis=0) * resolution


def _waveform_scalars(signals: np.ndarray) -> list[np.ndarray]:
    """RMS, kurtosis and crest factor per box.

    Kurtosis is the Pearson form, not the excess form: every quantity here has
    to stay positive to survive the log in the cross-side contrast.
    """
    rms = np.sqrt(np.square(signals).mean(axis=0))
    centred = signals - signals.mean(axis=0)
    variance = np.square(centred).mean(axis=0)
    kurtosis = np.power(centred, 4).mean(axis=0) / np.maximum(
        np.square(variance), config.NUMERICAL_FLOOR
    )
    crest = np.abs(signals).max(axis=0) / np.maximum(rms, config.NUMERICAL_FLOOR)
    return [rms, kurtosis, crest]


def _spectral_scalars(frequencies: np.ndarray, psd: np.ndarray) -> list[np.ndarray]:
    """Spectral centroid and dominant peak frequency per box."""
    total = np.maximum(psd.sum(axis=0), config.NUMERICAL_FLOOR)
    centroid = (frequencies[:, None] * psd).sum(axis=0) / total
    peak = frequencies[psd.argmax(axis=0)]
    return [centroid, peak]


def quantities(signals: np.ndarray, speed_ms: float) -> np.ndarray:
    """Every per-box quantity for one channel type: (len(QUANTITY_NAMES), 64).

    Public because explain.py has to show the reader the same per-box numbers the
    aggregates were taken over. Recomputing them there would let the explanation
    drift away from the prediction it claims to explain.
    """
    frequencies, psd = welch(
        signals, fs=config.SAMPLE_RATE_HZ, nperseg=config.WELCH_NPERSEG, axis=0
    )

    hz_bands = [_band_energy(psd, frequencies, low, high) for low, high in _HZ_BANDS]

    if speed_ms < config.STATIONARY_SPEED_MS:
        # lambda = speed / frequency has no value here, and NaN says so through
        # the aggregates and the log; a zero would claim a measurement and give -inf.
        wavelength_bands = [np.full(signals.shape[1], np.nan) for _ in _WAVELENGTH_BANDS]
    else:
        wavelength_bands = [
            _band_energy(psd, frequencies, speed_ms / high, speed_ms / low)
            for low, high in _WAVELENGTH_BANDS
        ]

    scalars = _waveform_scalars(signals) + _spectral_scalars(frequencies, psd)
    return np.vstack(hz_bands + wavelength_bands + scalars)


def extract(recording: Recording) -> np.ndarray:
    """Featurise one recording into FEATURE_NAMES order.

    Speed comes from the recording's own tachometer because the wavelength
    bands cannot be placed without it.
    """
    speed_ms = estimate_speed(recording.speed_channel)
    channels = ((VIBRATION, recording.vibration), (SHOCK, recording.shock))

    values: list[np.ndarray] = []
    for _, signals in channels:
        per_box = quantities(signals, speed_ms)
        per_side = [
            [function(per_box[:, boxes], axis=1) for function in _AGGREGATES]
            for boxes in _SIDE_INDEX
        ]
        for aggregates in per_side:
            values.extend(aggregates)

        side_i, side_ii = per_side
        floor = config.NUMERICAL_FLOOR
        values.extend(
            np.log10(np.maximum(first, floor)) - np.log10(np.maximum(second, floor))
            for first, second in zip(side_i, side_ii)
        )

    vector = np.concatenate(values)
    if vector.size != len(FEATURE_NAMES):
        raise ValueError(
            f"Built {vector.size} features for {recording.source_name}, "
            f"expected {len(FEATURE_NAMES)}."
        )
    return vector
