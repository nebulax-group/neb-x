"""Turn ACV case files into submission rows."""

from pathlib import Path

import pandas as pd

from . import config, dataset, features, rank


def predict(inputs: list[Path]) -> pd.DataFrame:
    """Return exactly the submission rows for this subsystem."""
    if not inputs:
        raise ValueError("No ACV input file was given.")
    records = []
    for path in inputs:
        path = Path(path)
        frame, cars = dataset.load_case(path)
        order = rank.rank_cars(features.temperature_excess(frame, cars))
        records.append(
            # file_id is the source name exactly as read - never rebuilt, never lowered.
            {"file_id": path.name, "ranked_cars": rank.to_ranked_string(order)}
        )
    return pd.DataFrame.from_records(records, columns=list(config.SUBMISSION_COLUMNS))
