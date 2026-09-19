"""Assemble the submission folder and the flat predictions.zip inside it.

Run as ``python -m src.submission.package [--team NAME]``.

The layout is the one in ``docs/problem_statement.md`` section 4.1, which is how
the organisers identify and score a submission:

    <Team Name>/
    |-- demo_video.<mp4|mov|...>     from video/out/, or a recording left in video/
    |-- predictions.zip              flat, only the CSVs, no subfolders
    |-- app/                         the source a judge runs
    `-- Optional_Items/
        `-- <Subsystem>/{code,model}/

Only subsystems that have produced a valid prediction file are included. A CSV
that fails validation stops the build rather than being zipped, because the
organisers score the zip directly and nothing downstream would notice.

Everything is written under ``submission/`` at the repository root, rebuilt from
scratch on every run and never committed.
"""

import argparse
import shutil
import zipfile
from pathlib import Path

from src.common.config import (
    DEFAULT_TEAM_NAME,
    DEMO_VIDEO_STEM,
    MODEL_DIRS,
    PREDICTION_PATHS,
    PREDICTIONS_ARCHIVE_NAME,
    REPO_ROOT,
    SRC_DIR,
    SUBMISSION_DIR,
    SUBSYSTEM_LABELS,
    SUBSYSTEMS,
    VIDEO_DIR,
    VIDEO_EXTENSIONS,
    VIDEO_OUT_DIR,
)

from .validate import validate_subsystem

APP_DIR_NAME = "app"
OPTIONAL_DIR_NAME = "Optional_Items"
CODE_DIR_NAME = "code"
MODEL_DIR_NAME = "model"

# What a judge needs in order to start the app. data/ and outputs/ are excluded:
# the datasets are the organisers' own and section 4.1 says not to send them back.
APP_CONTENTS = (
    "src",
    "scripts",
    ".streamlit",
    "requirements.txt",
    "install.sh",
    "install.bat",
    "submit.sh",
    "submit.bat",
    "README.md",
)

# Caches are regenerable and only make the folder bigger and slower to send.
IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", ".gitkeep")


def ready_subsystems() -> tuple[list[str], dict[str, list[str]]]:
    """Subsystems with a valid prediction file, and the problems of any that fail."""
    ready, broken = [], {}
    for subsystem in SUBSYSTEMS:
        problems = validate_subsystem(subsystem)
        if problems is None:
            continue
        if problems:
            broken[subsystem] = problems
        else:
            ready.append(subsystem)
    return ready, broken


def write_archive(subsystems: list[str], destination: Path) -> Path:
    """Zip the prediction CSVs flat, with no folder inside the archive."""
    path = destination / PREDICTIONS_ARCHIVE_NAME
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for subsystem in subsystems:
            source = PREDICTION_PATHS[subsystem]
            # arcname is the bare filename: a path here would nest the CSVs inside a
            # folder, which section 4.1 rules out.
            archive.write(source, arcname=source.name)
    return path


def copy_app(destination: Path) -> list[str]:
    """Copy the source a judge needs to run the app. Returns what was missing."""
    app = destination / APP_DIR_NAME
    app.mkdir(parents=True, exist_ok=True)

    missing = []
    for name in APP_CONTENTS:
        source = REPO_ROOT / name
        if not source.exists():
            missing.append(name)
            continue
        if source.is_dir():
            shutil.copytree(source, app / name, ignore=IGNORED, dirs_exist_ok=True)
        else:
            shutil.copy2(source, app / name)
    return missing


def copy_optional(subsystems: list[str], destination: Path) -> list[str]:
    """Copy each subsystem's code and trained model. Returns the folders written.

    The trained models travel here rather than in ``outputs/``, which is gitignored
    and so never reaches the machine that records the demo.
    """
    written = []
    for subsystem in subsystems:
        label = SUBSYSTEM_LABELS[subsystem]
        folder = destination / OPTIONAL_DIR_NAME / label

        code = SRC_DIR / subsystem
        if code.is_dir() and any(p for p in code.iterdir() if p.name != ".gitkeep"):
            shutil.copytree(code, folder / CODE_DIR_NAME, ignore=IGNORED, dirs_exist_ok=True)
            written.append(f"{label}/{CODE_DIR_NAME}")

        model = MODEL_DIRS[subsystem]
        if model.is_dir() and any(model.iterdir()):
            shutil.copytree(model, folder / MODEL_DIR_NAME, ignore=IGNORED, dirs_exist_ok=True)
            written.append(f"{label}/{MODEL_DIR_NAME}")
    return written


def find_video() -> Path | None:
    """The video to submit, or None if nobody has made one yet.

    Missing is a normal state rather than an error: the video is made once, at the
    end, and everything else has to be packageable before then.
    """
    # The rendered cut wins over a loose recording in video/, which is as likely to
    # be a superseded take nobody deleted as it is to be the one we mean to send.
    for folder in (VIDEO_OUT_DIR, VIDEO_DIR):
        if not folder.is_dir():
            continue
        found = sorted(
            item
            for item in folder.iterdir()
            if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS
        )
        if found:
            return found[0]
    return None


def copy_video(source: Path, destination: Path) -> Path:
    """Copy the demo video into the submission under the name section 4.1 asks for."""
    # Named for the deliverable rather than for whatever recorded it, but the
    # extension is kept so the file still plays.
    target = destination / f"{DEMO_VIDEO_STEM}{source.suffix.lower()}"
    shutil.copy2(source, target)
    return target


def build(team: str = DEFAULT_TEAM_NAME, root: Path | None = None) -> Path:
    """Assemble the submission folder and return it.

    Raises when a prediction file exists but does not match its schema: a bad CSV
    in the zip is scored as-is, so it must not be packaged by accident.
    """
    ready, broken = ready_subsystems()
    if broken:
        detail = "; ".join(
            f"{subsystem}: {' '.join(problems)}" for subsystem, problems in broken.items()
        )
        raise ValueError(f"Prediction files fail validation, refusing to package. {detail}")
    if not ready:
        raise ValueError(
            "No valid prediction files to package. Run a subsystem's predict step first."
        )

    root = SUBMISSION_DIR if root is None else Path(root)
    destination = root / team
    # Rebuilt from scratch every time, so a subsystem that was removed or renamed
    # cannot linger in the folder we send.
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    write_archive(ready, destination)
    missing_app = copy_app(destination)
    optional = copy_optional(ready, destination)
    source = find_video()
    video = None if source is None else copy_video(source, destination)

    print(f"packaged {len(ready)} of {len(SUBSYSTEMS)} subsystems: {', '.join(ready)}")
    print(f"  {PREDICTIONS_ARCHIVE_NAME}  {', '.join(PREDICTION_PATHS[s].name for s in ready)}")
    print(f"  {APP_DIR_NAME}/            {len(APP_CONTENTS) - len(missing_app)} items")
    if optional:
        print(f"  {OPTIONAL_DIR_NAME}/  {', '.join(optional)}")
    if video is not None:
        print(f"  {video.name}          from {source.parent}")

    print(f"\nsubmission folder: {destination}")

    outstanding = []
    if missing_app:
        outstanding.append(f"file not found, skipped: {', '.join(missing_app)}")
    if video is None:
        outstanding.append(
            "file not found, skipped: the demo video. Render it with scripts/render.sh, "
            f"or put a recording in {VIDEO_DIR}, then run this again. Section 4.1 does "
            "not score a subsystem without it."
        )
    if team == DEFAULT_TEAM_NAME:
        outstanding.append(
            f"the folder is named {DEFAULT_TEAM_NAME!r}, which is a placeholder. "
            "Re-run with --team to set the registered name."
        )
    missing_subsystems = [key for key in SUBSYSTEMS if key not in ready]
    if missing_subsystems:
        outstanding.append(
            f"no prediction file yet for: {', '.join(missing_subsystems)}. "
            "They join the zip automatically once their predict step runs."
        )

    if outstanding:
        print("\nnot submittable yet:")
        for note in outstanding:
            print(f"  - {note}")
    else:
        print("\nevery compulsory item is present.")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble the submission folder.")
    parser.add_argument(
        "--team",
        default=DEFAULT_TEAM_NAME,
        help=f"Team name, used as the top-level folder name (default {DEFAULT_TEAM_NAME}).",
    )
    parser.add_argument(
        "--into",
        type=Path,
        default=None,
        help=f"Where to build it (default {SUBMISSION_DIR}).",
    )
    arguments = parser.parse_args()

    try:
        build(arguments.team, arguments.into)
    except (OSError, ValueError) as error:
        raise SystemExit(f"Packaging failed: {error}")


if __name__ == "__main__":
    main()
