"""Select abnormal cycles and the current evidence needed for a door inspection."""

from . import config, dataset, features, segment
from .explain import _display_time, severity


def build(inputs, frame, panels):
    stream = dataset.load_stream(inputs[0])
    measurements = features.build(stream)
    bounds = segment.segment_bounds(stream)
    flags = frame["prediction"] == config.LABEL_ABNORMAL
    urgency = severity(flags)
    findings, chart = [], []
    for position, (_, prediction) in enumerate(frame.iterrows()):
        if prediction["prediction"] != config.LABEL_ABNORMAL:
            continue
        measured = measurements.iloc[position]
        start_time, start_date, _ = _display_time(prediction["start_time"])
        end_time, end_date, _ = _display_time(prediction["end_time"])
        findings.append({
            "source_file": inputs[0].name, "cycle": position + 1,
            "operation": bounds.iloc[position]["operation"],
            "start": f"{start_date} {start_time}", "end": f"{end_date} {end_time}",
            "status": config.LABEL_ABNORMAL, "priority": urgency,
            "mean_current_mA": round(float(measured["mean_current"]), 3),
            "typical_current_mA": round(float(measured["mean_current"] / measured["ratio"]), 3),
            "current_ratio": round(float(measured["ratio"]), 4),
        })
        chart.append({"label": f"Cycle {position + 1} ({measured['operation']})", "value": float(measured["ratio"]), "severity": urgency})
    recommendation = config.RECOMMENDATIONS[urgency]
    return {
        "recipient": "Door maintenance team",
        "summary": f"{len(findings)} abnormal-resistance cycles out of {len(frame)} assessed.",
        "checked_count": len(frame), "unit": "cycles", "findings": findings,
        "actions": ([recommendation["title"], "Review findings.csv for the flagged cycle times, operation and current evidence.", "Check for obstruction or mechanical resistance under the door inspection procedure.", "After inspection or corrective work, assess a fresh recording for recurring resistance."] if findings else [recommendation["title"], "Follow the normal inspection schedule and compare future recordings for new resistance flags."]),
        "method": "Fitted classifier using mean motor current relative to the median cycle of the same operation in this recording. Duration does not determine the classification.",
        "limitations": ["The comparison assumes representative normal cycles in the recording. Similar resistance throughout the recording can raise the baseline.", "A resistance flag does not establish the mechanical cause. Confirm by inspection."],
        "chart": {"title": "Flagged cycles: current relative to typical", "unit": "Current ratio (times typical)", "rows": chart},
    }
