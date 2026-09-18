"""Rail test files -> the submission rows, and the CSV on disk.

The function is the whole integration contract: the app calls predict() and
renders what comes back. Only this module and train.py write under outputs/.
"""

from pathlib import Path

import pandas as pd

from src.common.config import PREDICTION_PATHS, TEST_PATHS
from src.common.io import list_data_files
from src.rail import config

FILE_ID, PREDICTION = config.PREDICTION_COLUMNS


def predict(inputs: str | Path) -> pd.DataFrame:
    """Return exactly the submission rows for one rail file or folder of them.

    file_id is the source filename verbatim -- the organisers match on it, and a
    rebuilt name scores the subsystem zero however good the labels are.
    """
    files = list_data_files(inputs)
    # The checkpoint path arrives in phase 9. Until then, and whenever no
    # checkpoint exists, every file takes the majority label.
    return pd.DataFrame({
        FILE_ID: [path.name for path in files],
        PREDICTION: config.FALLBACK_LABEL,
    })


def main() -> None:
    frame = predict(TEST_PATHS[config.SUBSYSTEM_KEY])
    output = PREDICTION_PATHS[config.SUBSYSTEM_KEY]
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    print(f"{len(frame)} rows -> {output}")


if __name__ == "__main__":
    main()
