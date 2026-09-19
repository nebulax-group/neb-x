"""Tachometer square wave -> train speed in m/s. Nothing else.

90 teeth, and the output toggles as a tooth enters and again as it leaves
(docs/rail/info_kit.md section 2.1), so a window holds two edges per tooth.
"""

import numpy as np

from src.rail import config


def _count_edges(channel: np.ndarray) -> int:
    """Count 0/1 transitions, thresholding at the channel's own midpoint.

    The midpoint survives a different logic level, and gives a dead tachometer
    -- held at one level, so min == max -- zero edges rather than noise.
    """
    high = channel > (channel.min() + channel.max()) / 2
    return int(np.count_nonzero(np.diff(high)))


def estimate_speed(channel: np.ndarray) -> float:
    """Train speed in m/s, averaged over the window the channel covers.

    Returns 0.0 when the channel never transitions, as 38 training files do.
    Callers must read that as "undefined" -- see config.STATIONARY_SPEED_MS.
    """
    if channel.ndim != 1:
        raise ValueError(f"Expected one tachometer channel, got shape {channel.shape}.")
    if channel.size == 0:
        raise ValueError("Cannot estimate speed from an empty tachometer channel.")

    duration_s = channel.size / config.SAMPLE_RATE_HZ
    teeth = _count_edges(channel) / config.EDGES_PER_TOOTH
    revolutions = teeth / config.TACHOMETER_TEETH
    return revolutions * config.WHEEL_CIRCUMFERENCE_M / duration_s
