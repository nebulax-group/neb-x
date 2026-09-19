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
from typing import NamedTuple

import numpy as np
from scipy.signal import welch

from src.rail import config, features
from src.rail.dataset import load_recording
from src.rail.predict import load_checkpoint
from src.rail.speed import estimate_speed

VERDICT_HEADLINE_NORMAL = "No corrugation found"
VERDICT_HEADLINE_FAULT = "Corrugation on the {rail} rail"
# The margin the call rests on, in the measurement's own units, rather than the
# model's probability -- which is a statement about the training set, not a hit
# rate, and reads as a guarantee once it is printed beside the word "confident".
# Door counts cycles and ACV quotes degrees of separation for the same reason.
VERDICT_FAULT_DETAIL = (
    "{ratio:.1f}x louder than the other rail at {band} ripple spacing. "
    "A rail to inspect, not a measure of how worn it is."
)
VERDICT_CLEAR_DETAIL = "Neither rail stands out from the other at any ripple spacing."
VERDICT_STILL_DETAIL = "Recorded stationary, with nothing crossing the rails to measure."
VERDICT_BATCH = " Most suspected of the {count} files checked."

BATCH_TITLE = "Every file in this batch"
BATCH_CAPTION = (
    "One block per recording, in the order they were added, coloured by its call. "
    "Pick one to read what was measured on it. The verdict above describes the most "
    "suspected file only -- the download holds a row for every file either way."
)
BATCH_LEGEND_CLEAR = "No corrugation"
BATCH_LEGEND_FAULT = "Corrugation"
BATCH_CELL_DETAIL = "{name}: {call}. {margin} {speed}"
BATCH_MARGIN = "{ratio:.1f}x louder on the {rail} rail at {band}."
BATCH_MARGIN_EVEN = "{ratio:.1f}x between the two rails at {band}."
BATCH_MARGIN_STILL = "No wavelength reading: the train is stationary."
BATCH_SPEED = "Recorded at {speed:.1f} m/s."

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

STATIONARY_DETAIL = "stationary, so wavelength cannot be resolved"
MILLIMETRES_PER_METRE = 1000
METRES_PER_KILOMETRE = 1000
SECONDS_PER_HOUR = 3600

# The wavelength rows of features.quantities, found by name so that reordering the
# per-box quantities cannot silently point this at the Hz bands instead.
_WAVELENGTH_ROWS = np.array(
    [features.QUANTITY_NAMES.index(name) for name in features.WAVELENGTH_BAND_NAMES]
)

# The same seven cross-side contrasts as columns of the feature vector, so a file's
# margin is read out of the row the estimator classified rather than recomputed
# beside it. Names, not offsets: an added band or aggregate moves every index here.
_VIBRATION, _PRIMARY_AGGREGATE = config.CHANNEL_NAMES[0], config.AGGREGATES[0]
_CONTRAST_COLUMNS = np.array(
    [
        features.FEATURE_NAMES.index(f"{_VIBRATION}_contrast_{_PRIMARY_AGGREGATE}_{band}")
        for band in features.WAVELENGTH_BAND_NAMES
    ]
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


def _verdict(name: str, called: str, detail: str, count: int) -> dict:
    """The call itself, as the one panel a reader who reads nothing else will see.

    The severity beside it is rail's judgement and not the app's, which is why it
    is looked up here rather than derived from the probability: the model answers
    which rail is corrugated, so every fault is a caution and none is an alert.
    """
    severity = config.SEVERITIES[called]
    next_steps = config.RECOMMENDATIONS[severity]
    if count > 1:
        detail += VERDICT_BATCH.format(count=count)
    return {
        "kind": "verdict",
        "subject": name,
        "headline": (
            VERDICT_HEADLINE_FAULT.format(rail=called)
            if called in config.SIDE_LABELS
            else VERDICT_HEADLINE_NORMAL
        ),
        "severity": severity,
        "detail": detail,
        # Normal's copy names neither the rail nor the file, and format ignores what
        # it is not asked for, so both are supplied and one branch covers both calls.
        "recommendation": {
            "title": next_steps["title"].format(rail=called, file=name),
            "steps": tuple(step.format(rail=called) for step in next_steps["steps"])
            + (config.RECOMMENDATION_SCOPE,),
        },
    }


def _log_ratio(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    """log10(first / second), floored exactly as the feature vector floors it."""
    floor = config.NUMERICAL_FLOOR
    return np.log10(np.maximum(first, floor)) - np.log10(np.maximum(second, floor))


class _Batch(NamedTuple):
    """Every uploaded file's reading, taken in one pass over the batch."""

    paths: list[Path]
    matrix: np.ndarray  # (files, features) exactly as the estimator classified it
    speeds: np.ndarray  # (files,) m/s
    calls: list[str]
    confidence: np.ndarray  # (files,) the model's own probability for its call
    chosen: int  # the most suspected file, which the detailed panels describe


def _read_batch(inputs: list[Path], checkpoint: dict) -> _Batch:
    """Featurise and classify every upload, one recording at a time.

    Recordings are read and dropped rather than collected: sixty-eight of them
    held at once is ~2.7 GB against a 228-float row each. The file the detailed
    panels go on to describe is therefore read a second time, which costs one
    file's parse and keeps the peak flat however many are uploaded.
    """
    rows, speeds = [], []
    for path in inputs:
        recording = load_recording(path)
        speeds.append(estimate_speed(recording.speed_channel))
        rows.append(features.extract(recording))
    matrix = np.vstack(rows)

    estimator = checkpoint["estimator"]
    classes = list(estimator.classes_)
    probabilities = estimator.predict_proba(matrix)
    suspicion = 1.0 - probabilities[:, classes.index(config.LABEL_NORMAL)]
    return _Batch(
        paths=list(inputs),
        matrix=matrix,
        speeds=np.asarray(speeds, dtype=float),
        calls=[classes[index] for index in probabilities.argmax(axis=1)],
        confidence=probabilities.max(axis=1),
        chosen=int(np.argmax(suspicion)),
    )


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


def _margin(contrast: np.ndarray, called: str) -> tuple[int, int, float] | None:
    """The implicated rail, the band that implicates it, and by what ratio.

    None when the whole contrast row is undefined, which is a stationary file:
    without speed there is no wavelength to state a margin against.
    """
    if np.isnan(contrast).all():
        return None
    side, band = _side_and_band(contrast, called)
    return side, band, float(10 ** abs(contrast[band]))


def _cells(batch: _Batch) -> list[dict]:
    """One cell per uploaded file, in the order they were added.

    Every number comes out of the row the estimator classified, so a cell cannot
    disagree with the call printed on it.
    """
    cells = []
    for index, path in enumerate(batch.paths):
        called = batch.calls[index]
        found = _margin(batch.matrix[index, _CONTRAST_COLUMNS], called)
        if found is None:
            margin = BATCH_MARGIN_STILL
        else:
            side, band, ratio = found
            template = BATCH_MARGIN if called in config.SIDE_LABELS else BATCH_MARGIN_EVEN
            margin = template.format(
                ratio=ratio, rail=config.SIDE_LABELS[side], band=_BAND_LABELS[band]
            )
        speed = BATCH_SPEED.format(speed=batch.speeds[index])
        cells.append(
            {
                "label": f"{index + 1:02d}",
                "title": path.name,
                "subtitle": called,
                "status": called,
                "state": config.SEVERITIES[called],
                "fields": [
                    {
                        "label": "Call",
                        "value": called,
                        "detail": f"{_confidence(batch.confidence[index])} model probability",
                    },
                    {
                        "label": "Strongest contrast",
                        "value": "--" if found is None else f"{found[2]:.1f}x",
                        "detail": margin,
                    },
                    {
                        "label": "Train speed",
                        "value": f"{batch.speeds[index]:.1f} m/s",
                        "detail": "from this file's own tachometer",
                    },
                ],
                "detail": BATCH_CELL_DETAIL.format(
                    name=path.name, call=called, margin=margin, speed=speed
                ),
            }
        )
    return cells


def _batch_panel(batch: _Batch) -> dict:
    """Every file at once, so a batch is not represented by one card.

    The verdict describes the most suspected file alone. With sixty-eight
    uploaded that leaves every other flagged file visible only as a row in the
    table, which is the opposite of what a reader opening a batch wants.
    """
    return {
        "kind": "strip",
        "title": BATCH_TITLE,
        "caption": BATCH_CAPTION,
        "cells": _cells(batch),
        "legend": [
            {"state": config.SEVERITIES[config.LABEL_NORMAL], "label": BATCH_LEGEND_CLEAR},
            {"state": config.SEVERITIES[config.LABEL_SIDE_I], "label": BATCH_LEGEND_FAULT},
        ],
    }


def explain(inputs: list[Path]) -> list[dict]:
    """Panels explaining a prediction over the same files ``predict`` was given."""
    if not inputs:
        raise ValueError("No rail input files to explain.")

    # Raises when nothing has been trained, rather than explaining a fallback that
    # no longer exists. The app asks for the prediction first and shows that failure,
    # so this one is never the sentence a reader is left with.
    checkpoint = load_checkpoint()

    batch = _read_batch(inputs, checkpoint)
    path = batch.paths[batch.chosen]
    called = batch.calls[batch.chosen]
    confidence = float(batch.confidence[batch.chosen])
    speed_ms = float(batch.speeds[batch.chosen])
    moving = speed_ms >= config.STATIONARY_SPEED_MS

    # Read out of the classified row rather than recomputed from the recording:
    # the two are the same arithmetic, and one source cannot disagree with itself.
    contrast = batch.matrix[batch.chosen, _CONTRAST_COLUMNS]
    found = _margin(contrast, called)

    if found is None:
        detail = VERDICT_STILL_DETAIL
    elif called in config.SIDE_LABELS:
        detail = VERDICT_FAULT_DETAIL.format(ratio=found[2], band=_BAND_LABELS[found[1]])
    else:
        detail = VERDICT_CLEAR_DETAIL
    verdict = _verdict(path.name, called, detail, len(inputs))

    recording = load_recording(path)
    per_box = features.quantities(recording.vibration, speed_ms)
    kilometres_per_hour = speed_ms * SECONDS_PER_HOUR / METRES_PER_KILOMETRE
    speed_detail = (
        f"{kilometres_per_hour:.0f} km/h from the tachometer" if moving else STATIONARY_DETAIL
    )
    reading = {
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
                "label": "Model probability",
                "value": _confidence(confidence),
                "detail": "how sure the model is, not a measured hit rate",
            },
            {
                "label": "Train speed",
                "value": f"{speed_ms:.1f} m/s",
                "detail": speed_detail,
            },
        ],
    }

    # A batch is summarised by every file; one file is summarised by itself, and a
    # strip of a single cell is a control with nothing to choose between.
    workings = [_batch_panel(batch)] if len(inputs) > 1 else []

    if not moving:
        # No speed, no wavelength, and nothing crossing the rail to measure.
        return [verdict, *workings, reading]

    side, band, _ = found
    spectrum = {
        "kind": "line",
        "title": SPECTRUM_TITLE,
        "caption": SPECTRUM_CAPTION,
        "subject": path.name,
        "x_title": SPECTRUM_X_TITLE,
        "y_title": SPECTRUM_Y_TITLE,
        "points": _spectrum(recording.vibration, speed_ms),
    }
    localisation = {
        "kind": "bars",
        "title": LOCALISATION_TITLE,
        "caption": LOCALISATION_CAPTION,
        "subject": f"{path.name} · {config.SIDE_LABELS[side]} rail, "
        f"ripples {_BAND_LABELS[band]} apart",
        "value_title": LOCALISATION_VALUE_TITLE,
        "rows": _localisation(per_box, int(_WAVELENGTH_ROWS[band]), side),
    }
    # The app draws the first of the workings beside the verdict, so that slot goes
    # to whatever the verdict leaves unsaid: the rest of the batch when there is
    # one, and otherwise the evidence for the single call being made. The reading
    # panel never leads -- it restates the verdict in numbers.
    return [verdict, *workings, spectrum, reading, localisation]
