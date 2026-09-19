"""228 numbers in one flat vector, and nothing downstream checks what they mean.

The estimator, the checkpoint guard and explain.py all address these by position
or by name and none of them can notice the two disagreeing, so the alignment
between FEATURE_NAMES and the values extract() stacks is tested directly: move
one side of one channel by a known factor and check the named columns move by
the amount that factor implies, and no others move at all.
"""

import dataclasses

import numpy as np
import pytest

from src.rail import config, features

SCALE = 10.0
POWER_DECADES = 2.0  # band energies are squares, so a 10x amplitude is 100x energy
AMPLITUDE_DECADES = 1.0


def named(vector, predicate):
    return {
        name: value
        for name, value in zip(features.FEATURE_NAMES, vector)
        if predicate(name)
    }


def scale_boxes(recording, boxes, factor):
    """The same recording with one side of the vibration channel amplified."""
    vibration = recording.vibration.copy()
    vibration[:, list(boxes)] *= factor
    return dataclasses.replace(recording, vibration=vibration)


def test_the_feature_count_is_what_the_configured_dimensions_multiply_out_to():
    per_channel = len(config.SIDE_BOXES) + 1  # the two sides, plus their contrast
    expected = (
        len(config.CHANNEL_NAMES)
        * per_channel
        * len(config.AGGREGATES)
        * len(features.QUANTITY_NAMES)
    )
    assert len(features.FEATURE_NAMES) == expected == 228
    assert len(set(features.FEATURE_NAMES)) == len(features.FEATURE_NAMES)


def test_the_quantity_names_cover_both_band_sets_and_the_scalars():
    assert len(features.QUANTITY_NAMES) == len(config.HZ_BAND_EDGES) - 1 + len(
        config.WAVELENGTH_EDGES_M
    ) - 1 + 5
    assert set(features.WAVELENGTH_BAND_NAMES) <= set(features.QUANTITY_NAMES)
    # explain.py finds its rows by these names rather than by an offset.
    assert all(name in features.QUANTITY_NAMES for name in features.WAVELENGTH_BAND_NAMES)


def test_one_recording_extracts_to_exactly_the_named_columns(side_i):
    vector = features.extract(side_i)
    assert vector.shape == (len(features.FEATURE_NAMES),)
    assert np.isfinite(vector).all(), "a fast file resolves every band"


def quantity_of(name: str) -> str:
    return next(q for q in features.QUANTITY_NAMES if name.endswith("_" + q))


def energy_quantities() -> set[str]:
    """The quantities that scale with the square of the signal: every band."""
    return set(features.WAVELENGTH_BAND_NAMES) | {
        name for name in features.QUANTITY_NAMES if name.startswith("hz")
    }


def test_amplifying_one_rail_moves_the_columns_named_after_it_and_no_others(side_i):
    """The alignment check, and the reason this file exists.

    A 10x amplitude on Side I's vibration boxes is 100x the energy in every
    band, 10x the RMS, and nothing at all to the shape statistics or to shock.
    Each group of names therefore has its own arithmetic to answer to, and a
    vector stacked in a different order than FEATURE_NAMES spells fails several
    of them at once.
    """
    base = dict(zip(features.FEATURE_NAMES, features.extract(side_i)))
    after = dict(
        zip(features.FEATURE_NAMES, features.extract(scale_boxes(side_i, config.SIDE_I_BOXES, SCALE)))
    )
    energy = energy_quantities()

    for name in features.FEATURE_NAMES:
        quantity = quantity_of(name)
        if quantity in energy:
            ratio, decades = SCALE**2, POWER_DECADES
        elif quantity == "rms":
            ratio, decades = SCALE, AMPLITUDE_DECADES
        else:  # kurtosis, crest, centroid, peak_hz: shape, not scale
            ratio, decades = 1.0, 0.0

        if name.startswith("shock") or "side_ii" in name:
            assert after[name] == pytest.approx(base[name]), name
        elif "contrast" in name:  # a log10 ratio, so the move is additive
            assert after[name] - base[name] == pytest.approx(decades), name
        else:  # vibration_side_i_*, the raw quantity itself
            assert after[name] == pytest.approx(base[name] * ratio), name


def test_swapping_the_two_rails_negates_every_contrast_and_nothing_else(side_i):
    """The contrast is a log ratio of one named rail over the other, so the sign
    is the whole answer: Side I is its positive direction throughout."""
    base = features.extract(side_i)
    vibration = side_i.vibration.copy()
    vibration[:, list(config.SIDE_I_BOXES)] = side_i.vibration[:, list(config.SIDE_II_BOXES)]
    vibration[:, list(config.SIDE_II_BOXES)] = side_i.vibration[:, list(config.SIDE_I_BOXES)]
    swapped = features.extract(dataclasses.replace(side_i, vibration=vibration))

    contrast = named(base, lambda name: name.startswith("vibration_contrast"))
    after = named(swapped, lambda name: name.startswith("vibration_contrast"))
    assert after.keys() == contrast.keys()
    for name in contrast:
        assert after[name] == pytest.approx(-contrast[name], abs=1e-9), name
    # And the side blocks trade places rather than changing value.
    for name, value in named(base, lambda n: n.startswith("vibration_side_i_")).items():
        assert swapped[features.FEATURE_NAMES.index(name.replace("side_i_", "side_ii_"))] == pytest.approx(value)


def test_a_stationary_file_leaves_every_wavelength_band_undefined(still):
    """Not zero. Zero would claim the two rails measured the same thing exactly,
    which only a file with no speed can say and no file has grounds to."""
    vector = features.extract(still)
    wavelength = named(vector, lambda n: any(n.endswith("_" + b) for b in features.WAVELENGTH_BAND_NAMES))
    assert len(wavelength) == 84
    assert all(np.isnan(value) for value in wavelength.values())
    rest = named(vector, lambda n: not any(n.endswith("_" + b) for b in features.WAVELENGTH_BAND_NAMES))
    assert all(np.isfinite(value) for value in rest.values())


def test_a_band_too_narrow_for_welchs_bins_is_undefined_and_not_empty(crawling):
    """At 1.29 m/s the longest band spans 2.6-4.3 Hz and Welch resolves 2.44 Hz
    a bin, so no bin falls inside it. Summing to zero there would be a claim."""
    vector = features.extract(crawling)
    undefined = {name for name, value in zip(features.FEATURE_NAMES, vector) if np.isnan(value)}
    longest = features.WAVELENGTH_BAND_NAMES[-1]
    assert undefined == {name for name in features.FEATURE_NAMES if name.endswith("_" + longest)}
    assert len(undefined) == 12


@pytest.mark.parametrize("fixture", ["still", "crawling", "side_i"])
def test_nothing_a_side_is_summarised_by_lands_on_the_numerical_floor(request, fixture):
    """The floor keeps log10 finite for a dead channel; a live one reaching it
    would turn a real contrast into a fabricated +/-12.

    Individual boxes do reach it -- a shock channel whose PSD peaks at DC reports
    peak_hz as 0.0 -- so it is the aggregate over 32 boxes that has to clear it,
    and that is the number the contrast is actually taken of.
    """
    recording = request.getfixturevalue(fixture)
    vector = features.extract(recording)
    for name, value in named(vector, lambda n: "_contrast_" not in n).items():
        assert np.isnan(value) or value > config.NUMERICAL_FLOOR, (name, value)


def test_the_per_box_quantities_are_one_row_per_name_and_one_column_per_box(side_i):
    """explain.py indexes this matrix by name and by axle box, in that order."""
    per_box = features.quantities(side_i.vibration, 13.278)
    assert per_box.shape == (len(features.QUANTITY_NAMES), config.N_AXLE_BOXES)
