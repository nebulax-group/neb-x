"""Verify a fresh clone can find its packages, its paths and its data.

Run this first on every machine. It is a diagnostic, not part of the pipeline:
it reads and never writes. Exit code 0 means the environment is usable.
"""

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

REQUIRED_PACKAGES = ("numpy", "scipy", "pandas", "openpyxl", "sklearn", "streamlit")
MINIMUM_PYTHON = (3, 12)

# The shape of the data as shipped, per each subsystem's info kit. These are facts
# about the organisers' datasets, not tunables -- if one of them fails, a folder is
# incomplete. They move into <sub>/config.py once those packages exist.
EXPECTED_FILE_COUNTS = {
    "acv": (6, 1),
    "rail": (272, 68),
    "shm": (64, 16),
}

failures: list[str] = []


def record(passed: bool, label: str, detail: str = "") -> bool:
    print(f"  {'ok  ' if passed else 'FAIL'}  {label}{f'  {detail}' if detail else ''}")
    if not passed:
        failures.append(label)
    return passed


def check_python() -> None:
    print("\nPython")
    version = ".".join(str(part) for part in sys.version_info[:3])
    record(sys.version_info >= MINIMUM_PYTHON, f"python >= {'.'.join(map(str, MINIMUM_PYTHON))}", version)
    record(
        Path(sys.prefix) == REPO_ROOT / ".venv",
        "running inside the project .venv",
        sys.prefix,
    )


def check_packages() -> None:
    print("\nPackages")
    for name in REQUIRED_PACKAGES:
        try:
            module = importlib.import_module(name)
        except Exception as exc:  # an installed-but-unimportable wheel looks like this
            record(False, name, f"{type(exc).__name__}: {exc}")
        else:
            record(True, name, getattr(module, "__version__", "?"))


def check_paths(config) -> None:
    print("\nPaths")
    singles = ("REPO_ROOT", "DATA_DIR", "DOCS_DIR", "REFERENCE_DIR", "SUBMISSION_FORMAT_DIR")
    for name in singles:
        path = getattr(config, name)
        record(path.exists(), name, str(path.relative_to(REPO_ROOT) or "."))

    groups = (
        ("train", config.TRAIN_PATHS),
        ("test", config.TEST_PATHS),
        ("labels", config.LABEL_PATHS),
        ("example", config.EXAMPLE_PREDICTION_PATHS),
        ("info kit", config.INFO_KIT_PATHS),
    )
    for label, mapping in groups:
        for subsystem, path in mapping.items():
            record(path.exists(), f"{label:9s} {subsystem:5s}", str(path.relative_to(REPO_ROOT)))


def check_data(config, list_data_files, read_table) -> None:
    print("\nData file counts")
    for subsystem, (n_train, n_test) in EXPECTED_FILE_COUNTS.items():
        for split, expected, root in (
            ("train", n_train, config.TRAIN_PATHS[subsystem]),
            ("test", n_test, config.TEST_PATHS[subsystem]),
        ):
            try:
                found = len(list_data_files(root))
            except Exception as exc:
                record(False, f"{subsystem:5s} {split:5s}", f"{type(exc).__name__}: {exc}")
                continue
            record(found == expected, f"{subsystem:5s} {split:5s}", f"{found} files (expect {expected})")

    print("\nReadability")
    probes = (
        ("rail", config.TRAIN_PATHS["rail"] / "Train1.csv", {}, (10000, 129)),
        ("acv", config.TRAIN_PATHS["acv"] / "acv_case_01.xlsx", {}, None),
        ("door train", config.TRAIN_PATHS["door"], {}, None),
        ("door test", config.TEST_PATHS["door"], {}, None),
        ("shm", config.TRAIN_PATHS["shm"] / "train01.csv", {"header": None}, (581120, 1)),
    )
    for label, path, kwargs, expected_shape in probes:
        try:
            shape = read_table(path, **kwargs).shape
        except Exception as exc:
            record(False, f"read {label}", f"{type(exc).__name__}: {exc}")
            continue
        ok = expected_shape is None or shape == expected_shape
        record(ok, f"read {label}", f"{shape}{'' if expected_shape is None else f' (expect {expected_shape})'}")

    # SHM files are headerless. Reading one with pandas' defaults silently eats the
    # first stress sample as a column name, which no later step can detect.
    print("\nSHM header trap")
    path = config.TRAIN_PATHS["shm"] / "train01.csv"
    with_header = read_table(path).shape[0]
    without_header = read_table(path, header=None).shape[0]
    record(
        without_header == with_header + 1,
        "header=None recovers the first sample",
        f"{with_header} -> {without_header} rows",
    )


def main() -> None:
    check_python()
    check_packages()

    try:
        from src.common import config
        from src.common.io import list_data_files, read_table
    except Exception as exc:
        raise SystemExit(f"\ncannot import src.common ({type(exc).__name__}: {exc}) -- run from the repo root")

    check_paths(config)
    check_data(config, list_data_files, read_table)

    print()
    if failures:
        raise SystemExit(f"{len(failures)} check(s) failed: {', '.join(failures[:5])}"
                         + (" ..." if len(failures) > 5 else ""))
    print("all checks passed -- environment is ready")


if __name__ == "__main__":
    main()
