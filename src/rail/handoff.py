"""Turn rail's calls into a track inspection list: which rail, which stretch, how much louder.

A finding here is a recording the model named a rail for. Normal recordings are
not findings, and neither is a ranking: rail either names a rail or it does not.

Every number comes back through ``explain._read_batch``, the same pass the panels
are drawn from, so the folder a depot receives cannot disagree with the screen it
was prepared from. That costs one re-featurisation of the batch, which is what
door and acv pay here too.

The one value this module must never hand upward is a NaN: ``app/handoff.chart_svg``
refuses a non-finite bar, and rejecting one row there loses the whole rail report
to "review evidence is incomplete". A stationary recording has no ripple spacing
to quote, so it is listed as a finding with no margin and contributes no bar.
"""

from . import config
from .explain import _BAND_LABELS, _CONTRAST_COLUMNS, _confidence, _margin, _read_batch
from .predict import load_checkpoint

RECIPIENT = "Track maintenance / permanent way engineer"
STATUS = "Inspection candidate; corrugation depth not measured"
NO_MARGIN = "Not available: recorded stationary"

METHOD = (
    "Both rails are crossed by the same train at the same speed in the same second, so "
    "the contrast between them cancels speed, ballast noise and track elasticity and what "
    "is left is genuinely asymmetric. Axle-box vibration is compared side against side in "
    "seven bands of ripple spacing from 20 to 500 mm, aggregated across the 32 boxes of "
    "each rail, and a fitted classifier reads the whole set of bands rather than any one."
)

LIMITATIONS = (
    "The reading names a rail and a stretch, not a depth. Neither the three labels nor the "
    "Info Kit defines how worn a rail is, so nothing here measures severity and two flagged "
    "recordings cannot be ranked against each other by urgency.",
    "Each recording is one second of running over one section of track. Whether the ripple "
    "is new or growing is what decides grinding, and one pass cannot say it -- compare with "
    "the last run over the same section before ordering work.",
    "A stationary recording has nothing crossing the rails to measure. Ripple spacing cannot "
    "be resolved on one, and it is listed without a margin rather than reported clear.",
    "Of the three calls the model recovers Side I least reliably in cross-validation, so the "
    "absence of a Side I flag is weaker evidence than the absence of a Side II one.",
)

CHART_TITLE = "Recordings needing inspection: how much louder the named rail is"
CHART_UNIT = (
    "Times louder than the opposite rail at the implicated ripple spacing "
    "(1.0 would mean the two rails match)"
)


def _finding(name: str, called: str, speed_ms: float, probability: float, found) -> dict:
    """One flagged recording as a row of findings.csv, margin or no margin."""
    severity = config.SEVERITIES[called]
    row = {
        "source_file": name,
        "rail": called,
        "priority": severity,
        "status": STATUS,
        "train_speed_ms": round(speed_ms, 2),
        # Through explain's own formatter, which never rounds a probability up
        # into a certainty. A bare 1.0 in a column a depot reads is exactly the
        # claim that decision exists to avoid making.
        "model_probability": _confidence(probability),
    }
    if found is None:
        return {**row, "ripple_spacing": NO_MARGIN, "times_louder": NO_MARGIN}
    _, band, ratio = found
    return {**row, "ripple_spacing": _BAND_LABELS[band], "times_louder": round(ratio, 2)}


def build(inputs, frame, panels):
    batch = _read_batch(inputs, load_checkpoint())

    findings, chart, actions = [], [], []
    for index, path in enumerate(batch.paths):
        called = batch.calls[index]
        if called not in config.SIDE_LABELS:
            continue
        found = _margin(batch.matrix[index, _CONTRAST_COLUMNS], called)
        findings.append(
            _finding(path.name, called, float(batch.speeds[index]), float(batch.confidence[index]), found)
        )
        # No bar for a stationary recording: the finding is real, the margin is not.
        if found is not None:
            chart.append(
                {"label": f"{path.name} · {called}", "value": found[2], "severity": config.SEVERITIES[called]}
            )
        steps = config.RECOMMENDATIONS[config.SEVERITIES[called]]
        actions.append(steps["title"].format(rail=called, file=path.name))
        actions.extend(step.format(rail=called) for step in steps["steps"])

    clear = config.RECOMMENDATIONS[config.SEVERITY_CLEAR]
    if not findings:
        actions = [clear["title"], *clear["steps"]]
    actions.append(config.RECOMMENDATION_SCOPE)

    stationary = int((batch.speeds < config.STATIONARY_SPEED_MS).sum())
    summary = f"{len(findings)} of {len(frame)} recordings show corrugation on one rail."
    if stationary:
        # "N of the M recorded ..." rather than "N of them", which would read as
        # N of the findings -- a stationary recording is almost never one.
        summary += (
            f" {stationary} of the {len(frame)} recorded a stationary train, with nothing "
            "crossing the rails to measure, and cannot be assessed either way."
        )

    return {
        "recipient": RECIPIENT,
        "summary": summary,
        "checked_count": len(frame),
        "unit": "recordings",
        "findings": findings,
        "actions": list(dict.fromkeys(actions)),
        "method": METHOD,
        "limitations": list(LIMITATIONS),
        "chart": {"title": CHART_TITLE, "unit": CHART_UNIT, "rows": chart},
    }
