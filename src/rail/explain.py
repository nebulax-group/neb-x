"""Turn one run of the rail model into the panels the app draws beside the call.

``predict`` answers which rail is corrugated; this answers how it could tell.
Both rails are crossed by the same train at the same speed in the same second, so
the contrast between the two sides cancels the confounders the Info Kit lists --
speed, ballast noise, track elasticity -- and whatever is left is genuinely
asymmetric. That contrast is what the model reads and what these panels show.

Every number here is taken from ``features.quantities``, the same per-box
function the feature vector is built from, so the explanation cannot drift away
from the prediction it claims to explain.

Panels are plain dicts, not a type of ours, so the app can draw them without
importing this subsystem. The shapes are documented in ``src/app/services.py``.
"""

from pathlib import Path

import numpy as np
from scipy.signal import welch

from src.rail import config, features
from src.rail.dataset import load_recording
from src.rail.predict import load_checkpoint
from src.rail.speed import estimate_speed

METRICS_TITLE = "The reading this call rests on"
METRICS_CAPTION = (
    "Each axle box on one rail has an opposite number on the other, four per car "
    "on each side. The two rails are crossed together, so anything that shows on "
    "one and not the other is the track, not the train."
)

SPECTRUM_TITLE = "Which rail is louder, wavelength by wavelength"
SPECTRUM_CAPTION = (
    "Corrugation is a ripple worn into the railhead, so a wheel rolling over it "
    "rings at the spacing of the ripples rather than at a fixed pitch -- which is "
    "why this is drawn against wavelength and not frequency. Above the centre "
    "line the Side I rail is the louder of the two at that wavelength; below it, "
    "Side II. The model reads this curve in seven bands rather than at any one "
    "point: a narrow excursion turns up on sound track too, so it is the shape "
    "across the whole range that decides the call."
)
SPECTRUM_X_TITLE = "Ripple spacing along the rail (mm)"
SPECTRUM_Y_TITLE = "Side I against Side II (log ratio)"

LOCALISATION_TITLE = "Where along the train it was picked up"
LOCALISATION_CAPTION = (
    "The same measurement split by car. A train at line speed covers more than "
    "its own length in the second recorded here, so each car passes over its own "
    "stretch of track and a reading banked into one or two of them points at a "
    "specific stretch -- which is where an inspection would start. Concentration "
    "on its own does not decide anything: sound track shows it too."
)
LOCALISATION_VALUE_TITLE = "Share of that rail's vibration"

UNTRAINED_TITLE = "No trained model was used"
UNTRAINED_CAPTION = (
    "Every row above is the fallback answer, not a measurement. Fit a model with "
    "python -m src.rail.train and run this again."
)

STATIONARY_DETAIL = "stationary, so wavelength cannot be resolved"
MILLIMETRES_PER_METRE = 1000
METRES_PER_KILOMETRE = 1000
SECONDS_PER_HOUR = 3600

# The wavelength rows of features.quantities, found by name so that reordering the
# per-box quantities cannot silently point this at the Hz bands instead.
_WAVELENGTH_ROWS = np.array(
    [features.QUANTITY_NAMES.index(name) for name in features.WAVELENGTH_BAND_NAMES]
)
_SIDE_INDEX = tuple(np.fromiter(boxes, dtype=int) for boxes in config.SIDE_BOXES)
_BOX_CARS = np.asarray(config.BOX_CARS)

_BAND_LABELS = tuple(
    f"{round(low * MILLIMETRES_PER_METRE)}-{round(high * MILLIMETRES_PER_METRE)} mm"
    for low, high in zip(config.WAVELENGTH_EDGES_M, config.WAVELENGTH_EDGES_M[1:])
)


def _confidence(probability: float) -> str:
    """The model's probability, never rounded up into a certainty it never had."""
    return ">99%" if probability >= 0.995 else f"{probability:.0%}"


def _log_ratio(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    """log10(first / second), floored exactly as the feature vector floors it."""
    floor = config.NUMERICAL_FLOOR
    return np.log10(np.maximum(first, floor)) - np.log10(np.maximum(second, floor))


def _side_maxima(per_box: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The loudest box on each rail, per quantity.

    Maximum rather than median because the fault is localised: only some boxes
    ever cross the corrugated stretch, and a median is built to discard them.
    """
    return tuple(per_box[:, boxes].max(axis=1) for boxes in _SIDE_INDEX)


def _spectrum(vibration: np.ndarray, speed_ms: float) -> tuple[list[float], list[float]]:
    """The cross-side log ratio against wavelength, over the modelled range.

    The feature vector integrates this curve into seven bands; drawn whole, it
    shows a reader where inside a band the asymmetry actually sits.
    """
    frequencies, psd = welch(
        vibration, fs=config.SAMPLE_RATE_HZ, nperseg=config.WELCH_NPERSEG, axis=0
    )
    shortest, longest = config.WAVELENGTH_EDGES_M[0], config.WAVELENGTH_EDGES_M[-1]
    # lambda = speed / frequency, so the modelled wavelengths are a frequency window
    # that moves with the train. Bin zero is dropped with it: it has no wavelength.
    inside = (frequencies >= speed_ms / longest) & (frequencies <= speed_ms / shortest)
    if not inside.any():
        return [], []

    wavelength_mm = speed_ms / frequencies[inside] * MILLIMETRES_PER_METRE
    side_i, side_ii = (psd[np.ix_(inside, boxes)].max(axis=1) for boxes in _SIDE_INDEX)
    order = np.argsort(wavelength_mm)  # ascending, or the line doubles back on itself
    return wavelength_mm[order].tolist(), _log_ratio(side_i, side_ii)[order].tolist()


def _side_and_band(contrast: np.ndarray, called: str) -> tuple[int, int]:
    """The rail to draw, and the wavelength band that most implicates it.

    For a fault call this is the rail the model named, so the panel explains the
    call rather than offering a second opinion on it. Normal names no rail, so it
    falls to whichever is louder where the two differ most.
    """
    side = (
        config.SIDE_LABELS.index(called)
        if called in config.SIDE_LABELS
        else int(contrast[np.nanargmax(np.abs(contrast))] < 0)
    )
    # Side I is the positive direction of the log ratio and Side II the negative,
    # so the band that implicates a rail is the extreme in that rail's direction.
    signed = contrast if side == 0 else -contrast
    return side, int(np.nanargmax(signed))


def _localisation(per_box: np.ndarray, row: int, side: int) -> list[dict]:
    """Each car's share of one rail's energy in one wavelength band."""
    boxes = _SIDE_INDEX[side]
    energy = per_box[row, boxes]
    total = float(energy.sum())
    if not np.isfinite(total) or total <= 0:
        return []

    cars = _BOX_CARS[boxes]
    rows = []
    for car in range(1, config.CARS + 1):
        held = energy[cars == car]
        rows.append(
            {
                "label": f"Car {car}",
                "value": float(held.sum()) / total,
                "detail": f"{held.size} axle boxes",
            }
        )
    return rows


def _subject(inputs: list[Path], checkpoint: dict) -> tuple[Path, str, float]:
    """The file worth drawing, its call, and the model's confidence in it.

    The most suspected file rather than the first: a reader opening a batch of
    sixty-eight wants the one that needs attention, and when nothing is suspected
    the least-healthy file is still the most informative thing to show.
    """
    estimator = checkpoint["estimator"]
    classes = list(estimator.classes_)
    probabilities = estimator.predict_proba(
        np.vstack([features.extract(load_recording(path)) for path in inputs])
    )
    suspicion = 1.0 - probabilities[:, classes.index(config.LABEL_NORMAL)]
    chosen = int(np.argmax(suspicion))
    return (
        inputs[chosen],
        classes[int(np.argmax(probabilities[chosen]))],
        float(probabilities[chosen].max()),
    )


def explain(inputs: list[Path]) -> list[dict]:
    """Panels explaining a prediction over the same files ``predict`` was given."""
    if not inputs:
        raise ValueError("No rail input files to explain.")

    checkpoint = load_checkpoint()
    if checkpoint is None:
        # Saying so is the whole panel. A fallback that looks like a result is
        # worse than no explanation at all.
        return [
            {
                "kind": "metrics",
                "title": UNTRAINED_TITLE,
                "caption": UNTRAINED_CAPTION,
                "items": [
                    {
                        "label": "Assessment",
                        "value": config.FALLBACK_LABEL,
                        "detail": f"assumed for all {len(inputs)} files",
                    }
                ],
            }
        ]

    path, called, confidence = _subject(inputs, checkpoint)
    recording = load_recording(path)
    speed_ms = estimate_speed(recording.speed_channel)
    moving = speed_ms >= config.STATIONARY_SPEED_MS

    per_box = features.quantities(recording.vibration, speed_ms)
    side_i, side_ii = _side_maxima(per_box)
    contrast = _log_ratio(side_i, side_ii)[_WAVELENGTH_ROWS]

    speed_detail = (
        f"{speed_ms * SECONDS_PER_HOUR / METRES_PER_KILOMETRE:.0f} km/h from the tachometer"
        if moving
        else STATIONARY_DETAIL
    )
    panels = [
        {
            "kind": "metrics",
            "title": METRICS_TITLE,
            "caption": METRICS_CAPTION,
            "subject": path.name,
            "items": [
                {
                    "label": "Assessment",
                    "value": called,
                    "detail": f"most suspected of the {len(inputs)} files checked"
                    if len(inputs) > 1
                    else "for this recording",
                },
                {
                    "label": "Confidence",
                    "value": _confidence(confidence),
                    "detail": "the model's own probability for that call",
                },
                {
                    "label": "Train speed",
                    "value": f"{speed_ms:.1f} m/s",
                    "detail": speed_detail,
                },
            ],
        }
    ]

    if not moving:
        # No speed, no wavelength, and nothing crossing the rail to measure.
        return panels

    side, band = _side_and_band(contrast, called)
    panels.append(
        {
            "kind": "line",
            "title": SPECTRUM_TITLE,
            "caption": SPECTRUM_CAPTION,
            "subject": path.name,
            "x_title": SPECTRUM_X_TITLE,
            "y_title": SPECTRUM_Y_TITLE,
            "points": _spectrum(recording.vibration, speed_ms),
        }
    )
    panels.append(
        {
            "kind": "bars",
            "title": LOCALISATION_TITLE,
            "caption": LOCALISATION_CAPTION,
            "subject": f"{path.name} · {config.SIDE_LABELS[side]} rail, "
            f"ripples {_BAND_LABELS[band]} apart",
            "value_title": LOCALISATION_VALUE_TITLE,
            "rows": _localisation(per_box, int(_WAVELENGTH_ROWS[band]), side),
        }
    )
    return panels
