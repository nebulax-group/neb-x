"""Turn each train's ranking into a short inspection shortlist, never a leak claim."""

import pandas as pd

from . import config, dataset, features
from .explain import _verdict


def build(inputs, frame, panels):
    findings, chart, actions = [], [], []
    for path in inputs:
        recording, cars = dataset.load_case(path)
        excess = features.temperature_excess(recording, cars)
        order = frame.loc[frame["file_id"] == path.name, "ranked_cars"].iloc[0].split(config.RANKED_CARS_SEPARATOR)
        table = pd.DataFrame({"car_id": order, "temperature_excess": [excess[car] for car in order]})
        verdict = _verdict(path, table)
        lead = float(table.iloc[0]["temperature_excess"] - table.iloc[1]["temperature_excess"]) if len(table) > 1 else None
        count = 2 if lead is not None and lead < config.CLEAR_LEAD_DEGREES else 1
        for rank, car in enumerate(order[:count], start=1):
            value = float(excess[car])
            findings.append({
                "source_file": path.name, "car_id": car, "rank": rank,
                "priority": verdict["severity"], "status": "Inspection candidate; leak unconfirmed",
                "mean_temperature_excess_C": round(value, 3),
                "lead_over_second_C": round(lead, 3) if lead is not None and pd.notna(lead) else "Not available",
            })
            chart.append({"label": f"{path.name} / Car {car}", "value": value, "severity": verdict["severity"]})
        actions.extend([f"{path.name}: {verdict['recommendation']['title']}", *verdict["recommendation"]["steps"]])
    return {
        "recipient": "ACV maintenance team",
        "summary": f"{len(findings)} cars shortlisted across {len(inputs)} recordings for inspection, not confirmed leaks.",
        "checked_count": sum(len(value.split(config.RANKED_CARS_SEPARATOR)) for value in frame["ranked_cars"]),
        "unit": "cars across recordings", "findings": findings,
        "actions": list(dict.fromkeys(actions)),
        "method": f"Cars ranked by average cabin temperature minus their own cooling target. Include the first car and the runner-up when their lead is below {config.CLEAR_LEAD_DEGREES} degrees C.",
        "limitations": ["Every recording produces a ranking, even when all cars are below their target. First place is not confirmation of a leak.", "Readings from different recordings must not be treated as the same train without checking the source records."],
        "chart": {"title": "Inspection candidates: temperature above own target", "unit": "Temperature excess (degrees C; negative means below target)", "rows": chart},
    }
