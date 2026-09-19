"""Speed places every wavelength band, so an error here moves all 84 of them.

The anchor these tests use is physical rather than algebraic: 90 teeth at two
edges each is 180 edges per wheel revolution, so a channel showing 180 edges in
one second is a wheel turning once a second, and the train is covering one
circumference in that second. Asserting the formula back at itself would pass
for any constant in it.
"""

import numpy as np
import pytest

from src.rail import config
from src.rail.speed import estimate_speed

EDGES_PER_REVOLUTION = config.TACHOMETER_TEETH * config.EDGES_PER_TOOTH


def square_wave(
    edges: int, samples: int = config.SAMPLES_PER_FILE, low: float = 0.0, high: float = 1.0
) -> np.ndarray:
    """A tachometer channel holding exactly ``edges`` transitions, evenly spaced.

    ``edges`` transitions need ``edges + 1`` level runs between them: the first
    run is entered without a transition, which is the fencepost the counting in
    speed.py is on the other side of.
    """
    boundaries = np.linspace(0, samples, edges + 2, dtype=int)
    assert np.all(np.diff(boundaries) > 0), "too many edges to place in that many samples"
    channel = np.full(samples, low, dtype=float)
    for level, (start, stop) in enumerate(zip(boundaries, boundaries[1:])):
        channel[start:stop] = high if level % 2 else low
    return channel


def test_one_wheel_revolution_per_second_is_one_circumference_per_second():
    speed = estimate_speed(square_wave(EDGES_PER_REVOLUTION))
    assert speed == pytest.approx(config.WHEEL_CIRCUMFERENCE_M)


def test_speed_is_proportional_to_the_edges_counted():
    single = estimate_speed(square_wave(EDGES_PER_REVOLUTION))
    for revolutions in (2, 4, 7):
        speed = estimate_speed(square_wave(EDGES_PER_REVOLUTION * revolutions))
        assert speed == pytest.approx(single * revolutions)


def test_a_shorter_window_at_the_same_rate_reads_the_same_speed():
    """Edges are divided by the duration the channel covers, not by its length."""
    full = estimate_speed(square_wave(EDGES_PER_REVOLUTION, config.SAMPLES_PER_FILE))
    half = estimate_speed(square_wave(EDGES_PER_REVOLUTION // 2, config.SAMPLES_PER_FILE // 2))
    assert half == pytest.approx(full)


@pytest.mark.parametrize("low, high", [(0.0, 1.0), (0.0, 5.0), (-1.0, 1.0), (2.0, 3.5)])
def test_the_midpoint_threshold_survives_a_different_logic_level(low, high):
    """Thresholding at the channel's own midpoint, not at a hard-coded 0.5."""
    speed = estimate_speed(square_wave(EDGES_PER_REVOLUTION, low=low, high=high))
    assert speed == pytest.approx(config.WHEEL_CIRCUMFERENCE_M)


@pytest.mark.parametrize("level", [0.0, 1.0, -3.0])
def test_a_tachometer_stuck_at_one_level_reads_zero_and_does_not_divide_by_it(level):
    """38 training files arrive like this. min == max, so the midpoint is that level."""
    assert estimate_speed(np.full(config.SAMPLES_PER_FILE, level)) == 0.0


def test_a_channel_that_is_not_one_series_is_refused_rather_than_flattened():
    with pytest.raises(ValueError, match="one tachometer channel"):
        estimate_speed(np.zeros((config.SAMPLES_PER_FILE, 2)))


def test_an_empty_channel_is_refused_rather_than_dividing_by_zero_duration():
    with pytest.raises(ValueError, match="empty tachometer channel"):
        estimate_speed(np.array([]))


def test_the_named_recordings_read_the_speeds_they_were_chosen_for(still, crawling, side_i):
    """Through the real channel, not a synthetic one: the 0/1 wave is real too."""
    assert estimate_speed(still.speed_channel) == 0.0
    assert estimate_speed(crawling.speed_channel) == pytest.approx(1.291, abs=0.01)
    assert estimate_speed(side_i.speed_channel) == pytest.approx(13.278, abs=0.01)
    # Each side of the fault floor, which is what the two fixtures are for.
    assert estimate_speed(side_i.speed_channel) >= config.FAST_SPEED_MS
    assert estimate_speed(crawling.speed_channel) < config.FAST_SPEED_MS
