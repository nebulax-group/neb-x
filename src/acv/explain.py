"""Turn one ACV ranking into the panels the app draws beside it.

``predict`` answers which car to open first; this answers how far ahead of the
next one it is, which for a ranking is the whole of the confidence. Every figure
comes from ``report.confirmation`` so the panels and the bench workbook cannot
drift apart.

Nothing here calls a leak. The task is to order eight cars, and it produces an
order for any file at all, so the copy says which car to check and how clear the
margin is, and never that one is faulty. The shapes are documented in
``src/app/services.py``.
"""

from pathlib import Path

import pandas as pd

from . import report
from .config import (
    CLEAR_LEAD_DEGREES,
    RECOMMENDATION_CLOSE,
    RECOMMENDATION_FIRST,
    RECOMMENDATION_STEPS,
    SEVERITY_CAUTION,
    SEVERITY_DANGER,
)

VERDICT_HEADLINE = "Car {car}, check first"
VERDICT_SEPARATED = "{lead:.2f} degrees clear of Car {second}. A ranking, not a confirmed leak."
VERDICT_FLAT = "Only {lead:.2f} degrees clear of Car {second}. Check both."
VERDICT_SINGLE = "The only car in this file."

BARS_TITLE = "How far ahead the first car is"
BARS_CAPTION = (
    "Every file ranks its cars, so one is always first. The gap back to second place "
    "is what says how much weight to put on it."
)
BARS_VALUE_TITLE = "Share of the spread between cars"
BARS_LABEL = "Car {car}"
BARS_DETAIL = "{excess:+.2f} against its own target"

METRICS_TITLE = "What the ranking is built on"
METRICS_CAPTION = (
    "A leaking unit cannot hold its own setpoint, so each car is measured against its "
    "own target and never against the other cars."
)
DUTY_DETAIL = "spread across all cars, too flat to confirm anything"


def _lead(table: pd.DataFrame) -> float:
    """Degrees between the top car and the runner up."""
    excess = table["temperature_excess"]
    return float(excess.iloc[0] - excess.iloc[1])


def severity(table: pd.DataFrame) -> str:
    """How clear cut the ordering is. Never clear; see the note in config.py.

    Two conditions, because either one alone misleads: a car has to be failing to
    hold its own target at all, and it has to be doing so by a margin the rest of
    the train is not.
    """
    if len(table) < 2:
        return SEVERITY_CAUTION
    warm = float(table["temperature_excess"].iloc[0]) > 0
    if warm and _lead(table) >= CLEAR_LEAD_DEGREES:
        return SEVERITY_DANGER
    return SEVERITY_CAUTION


def _shares(table: pd.DataFrame) -> list[dict]:
    """Each car's warmth above the coolest car, as a share of the whole spread.

    Measured from the coolest car rather than from each car's own target, because
    the targets differ and several cars can sit below theirs at once; against a
    common floor the shares are non-negative and add to one, which is what makes
    the top car's lead readable as a proportion rather than as a raw offset.
    """
    excess = table["temperature_excess"]
    lead = excess - excess.min()
    total = float(lead.sum())
    if total <= 0:
        return []
    return [
        {
            "label": BARS_LABEL.format(car=car),
            "value": float(value) / total,
            "detail": BARS_DETAIL.format(excess=float(own)),
        }
        for car, value, own in zip(table["car_id"], lead, excess)
    ]


def _verdict(path: Path, table: pd.DataFrame) -> dict:
    top = table["car_id"].iloc[0]
    next_title = RECOMMENDATION_FIRST.format(car=top)
    cars = f"Car {top}"
    if len(table) < 2:
        detail = VERDICT_SINGLE
    else:
        lead = _lead(table)
        template = (
            VERDICT_SEPARATED if lead >= CLEAR_LEAD_DEGREES else VERDICT_FLAT
        )
        detail = template.format(lead=lead, second=table["car_id"].iloc[1])
        if lead < CLEAR_LEAD_DEGREES:
            second = table["car_id"].iloc[1]
            next_title = RECOMMENDATION_CLOSE.format(car=top, second=second)
            cars = f"Car {top} and Car {second}"
    return {
        "kind": "verdict",
        "subject": path.name,
        "headline": VERDICT_HEADLINE.format(car=top),
        "severity": severity(table),
        "detail": detail,
        "recommendation": {
            "title": next_title,
            "steps": [step.format(cars=cars) for step in RECOMMENDATION_STEPS],
        },
    }


def explain(inputs: list[Path]) -> list[dict]:
    """Panels explaining a ranking over the same files ``predict`` was given.

    One verdict per file: each workbook is a different train, so each carries its
    own answer. The charts describe the file whose top car stands out most, which
    is the one worth opening first when several are uploaded together.
    """
    if not inputs:
        raise ValueError("No ACV input file to explain.")

    tables = {Path(path): report.confirmation(path) for path in inputs}
    subject, table = max(
        tables.items(), key=lambda item: _lead(item[1]) if len(item[1]) > 1 else 0.0
    )
    duty = table["cooling_duty_cycle"]

    runner_up = (
        [
            {
                "label": "Clear of second",
                "value": f"{_lead(table):.2f}",
                "detail": f"degrees ahead of Car {table['car_id'].iloc[1]}",
            }
        ]
        if len(table) > 1
        else []
    )

    return [
        *(_verdict(path, one) for path, one in tables.items()),
        {
            "kind": "bars",
            "title": BARS_TITLE,
            "caption": BARS_CAPTION,
            "subject": subject.name,
            "value_title": BARS_VALUE_TITLE,
            "rows": _shares(table),
        },
        {
            "kind": "metrics",
            "title": METRICS_TITLE,
            "caption": METRICS_CAPTION,
            "subject": subject.name,
            "items": [
                {
                    "label": "Check first",
                    "value": f"Car {table['car_id'].iloc[0]}",
                    "detail": f"{table['temperature_excess'].iloc[0]:+.2f} against its own target",
                },
                *runner_up,
                {
                    "label": "Cooling duty",
                    "value": f"{float(duty.max() - duty.min()):.3f}",
                    "detail": DUTY_DETAIL,
                },
            ],
        },
    ]
