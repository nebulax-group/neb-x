"""Extract the training features and cache them. Writes under outputs/.

The cache holds every training file. Dropping the two byte-identical duplicates
is a fitting decision, so it happens where the model is fit, not here.
"""

import time
from pathlib import Path

import numpy as np

from src.common.config import MODEL_DIRS, TRAIN_PATHS
from src.common.io import list_data_files
from src.rail import config, dataset, features

FEATURE_CACHE_PATH = MODEL_DIRS[config.SUBSYSTEM_KEY] / config.FEATURE_CACHE_NAME


def extract_features(directory: str | Path) -> tuple[np.ndarray, list[str]]:
    """Featurise every file in a folder, one recording at a time.

    Streamed rather than loaded up front: 272 recordings held together would be
    ~2.7 GB, against 744 KB of features.
    """
    matrix: list[np.ndarray] = []
    names: list[str] = []
    for path in list_data_files(directory):
        recording = dataset.load_recording(path)
        names.append(recording.source_name)
        matrix.append(features.extract(recording))
    return np.vstack(matrix), names


def training_features(refresh: bool = False) -> tuple[np.ndarray, list[str]]:
    """The cached training matrix and its filenames, extracting it if missing."""
    if refresh or not FEATURE_CACHE_PATH.exists():
        matrix, names = extract_features(TRAIN_PATHS[config.SUBSYSTEM_KEY])
        FEATURE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            FEATURE_CACHE_PATH,
            matrix=matrix,
            files=np.array(names),
            columns=np.array(features.FEATURE_NAMES),
        )
        return matrix, names

    cached = np.load(FEATURE_CACHE_PATH, allow_pickle=False)
    if tuple(cached["columns"]) != features.FEATURE_NAMES:
        raise ValueError(
            f"{FEATURE_CACHE_PATH.name} was built from a different feature set. "
            "Re-extract with refresh=True."
        )
    return cached["matrix"], list(cached["files"])


def main() -> None:
    started = time.perf_counter()
    matrix, names = training_features(refresh=True)
    print(
        f"{len(names)} files x {matrix.shape[1]} features "
        f"in {time.perf_counter() - started:.0f}s -> {FEATURE_CACHE_PATH}"
    )


if __name__ == "__main__":
    main()
