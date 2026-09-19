"""Export individual stress recordings that meet the existing review thresholds."""

from . import config
from .explain import severity


def build(inputs, frame, panels):
    findings, chart, actions = [], [], []
    for _, row in frame.iterrows():
        damage = float(row[config.PREDICTION_COLUMN])
        priority = severity(damage)
        if priority == config.SEVERITY_CLEAR:
            continue
        name = row["file_id"]
        findings.append({
            "source_file": name, "priority": priority,
            "recording_damage": damage, "modelled_budget_percent": round(damage * 100, 3),
            "status": "Model fatigue limit reached" if priority == config.SEVERITY_DANGER else "Engineering review advised",
        })
        chart.append({"label": name, "value": damage, "severity": priority})
        recommendation = config.RECOMMENDATIONS[priority]
        actions.extend([recommendation["title"].format(file=name), *recommendation["steps"]])
    return {
        "recipient": "Structural maintenance / responsible structural engineer",
        "summary": f"{len(findings)} of {len(frame)} recordings meet the model's review criteria. Highest per-recording damage: {float(frame[config.PREDICTION_COLUMN].max()):.1%}. Prior damage is unknown.",
        "checked_count": len(frame), "unit": "recordings", "findings": findings,
        "actions": list(dict.fromkeys(actions)) or list(config.RECOMMENDATIONS[config.SEVERITY_CLEAR]["steps"]),
        "method": "Rainflow cycle counting and a fitted S-N curve. Review when a further identical recording would exceed D = 1; alert when this recording's D is at least 1.",
        "limitations": ["Prior accumulated damage is unknown. A low per-recording value does not establish remaining lifetime or fitness for service.", "Files are not summed: measurement point and non-overlapping collection periods must be confirmed first.", "Thresholds describe the model's assessment, not an LTA operating or maintenance standard."],
        "chart": {"title": "Recordings needing review: estimated damage", "unit": "Damage D per recording (model limit D = 1)", "rows": chart},
    }
