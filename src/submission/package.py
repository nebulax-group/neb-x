"""Assemble the submission folder and the flat predictions.zip inside it.

Run as ``python -m src.submission.package [--team NAME]``.

The layout is the one in ``docs/problem_statement.md`` section 4.1, which is how
the organisers identify and score a submission:

    <Team Name>/
    |-- demo_video.<mp4|mov|...>     from video/out/, or a recording left in video/
    |-- predictions.zip              flat, only the CSVs, no subfolders
    |-- app/                         run.sh, the app's own code, and its checkpoints
    `-- Optional_Items/
        |-- write_up.<pdf|docx|md>   from the repository root, if one has been written
        `-- <Subsystem>/{code,model}/

Only subsystems that have produced a valid prediction file are included. A CSV
that fails validation stops the build rather than being zipped, because the
organisers score the zip directly and nothing downstream would notice. Everything
else that is absent is reported at the end and the folder is still built: the video
and the write-up are made last, and the folder has to be buildable before they exist.

The folder is built at the repository root under the team's own name, rebuilt from
scratch on every run and never committed. What gets uploaded is that folder itself,
so nothing wraps it that could be sent by mistake.
"""

import argparse
import shutil
import zipfile
from pathlib import Path

from src.common.config import (
    DEFAULT_TEAM_NAME,
    DEMO_VIDEO_STEM,
    MODELS_DIR,
    MODEL_DIRS,
    PREDICTION_PATHS,
    PREDICTIONS_ARCHIVE_NAME,
    REPO_ROOT,
    REQUIREMENTS_PATH,
    SRC_DIR,
    STREAMLIT_CONFIG_PATH,
    SUBMISSION_ROOT,
    SUBSYSTEM_LABELS,
    SUBSYSTEMS,
    VIDEO_DIR,
    VIDEO_EXTENSIONS,
    VIDEO_OUT_DIR,
    WRITE_UP_DIR,
    WRITE_UP_EXTENSIONS,
    WRITE_UP_STEM,
)

from .validate import validate_subsystem

APP_DIR_NAME = "app"
OPTIONAL_DIR_NAME = "Optional_Items"
CODE_DIR_NAME = "code"
MODEL_DIR_NAME = "model"

# Section 4.1 item 3 asks for the app, so app/ holds what starts the app and nothing
# else. The rest of this repository is how the app is developed, trained and submitted,
# and a wrapper a judge cannot run reads worse than an absent one: scripts/render.sh
# needs manim, which requirements.txt deliberately lacks, and the train wrappers need
# a data/ that section 4.1 says not to send back in any case.
# Source paths relative to the repository root; each is copied under its bare name to
# the top of app/, which is where the runner looks for requirements.txt however the
# repository chooses to file it.
APP_CONTENTS = (
    STREAMLIT_CONFIG_PATH.parent.relative_to(REPO_ROOT),
    REQUIREMENTS_PATH.relative_to(REPO_ROOT),
)

# The packages the app imports: its own shell, the shared layer, and the four
# subsystems it resolves by name. src/submission/ and src/video/ are not among them.
APP_PACKAGES = ("app", "common", *SUBSYSTEMS)

# Its one entry point, copied to the top of app/ where a judge will look for it. The
# repository's own scripts/app.sh cannot serve: it climbs to a repository root that
# does not exist there and calls an install.sh that does not ship.
RUNNER_DIR = Path(__file__).resolve().parent / "runner"
RUNNERS = ("run.sh", "run.bat")
# Set rather than inherited. A lost executable bit is how ./submit.sh came to fail on
# a fresh clone, and the same bit is the only thing between a judge and the app.
RUNNER_MODE = 0o755

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


def copy_checkpoints(subsystems: list[str], destination: Path) -> list[str]:
    """Put each subsystem's trained model where the copied app will look for it.

    ``MODEL_DIRS`` hangs off ``REPO_ROOT``, which inside the copied app is ``app/``,
    so landing them at the same relative path means no subsystem config has to learn
    a second one. Without this the app ships complete, reports every system as ready
    and fails on the first click, because ``is_available`` only imports the module.

    A subsystem with no directory needs no model: it is only on this list because it
    already predicted its held-out inputs, which it did without one.
    """
    relative = MODELS_DIR.relative_to(REPO_ROOT)
    shipped = []
    for subsystem in subsystems:
        source = MODEL_DIRS[subsystem]
        if not source.is_dir() or not any(source.iterdir()):
            continue
        shutil.copytree(
            source,
            destination / APP_DIR_NAME / relative / subsystem,
            ignore=IGNORED,
            dirs_exist_ok=True,
        )
        shipped.append(subsystem)
    return shipped


def copy_app(destination: Path) -> list[str]:
    """Copy what starts the app, and only that. Returns what was missing."""
    app = destination / APP_DIR_NAME
    app.mkdir(parents=True, exist_ok=True)

    missing = []
    for name in APP_CONTENTS:
        source = REPO_ROOT / name
        if not source.exists():
            missing.append(str(name))
            continue
        target = app / name.name
        if source.is_dir():
            shutil.copytree(source, target, ignore=IGNORED, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)

    package_root = app / SRC_DIR.name
    package_root.mkdir(parents=True, exist_ok=True)
    marker = SRC_DIR / "__init__.py"
    if marker.is_file():
        shutil.copy2(marker, package_root / marker.name)
    else:
        missing.append(str(marker.relative_to(REPO_ROOT)))
    for name in APP_PACKAGES:
        source = SRC_DIR / name
        if not source.is_dir():
            missing.append(str(source.relative_to(REPO_ROOT)))
            continue
        shutil.copytree(source, package_root / name, ignore=IGNORED, dirs_exist_ok=True)

    for name in RUNNERS:
        source = RUNNER_DIR / name
        if not source.is_file():
            missing.append(name)
            continue
        target = shutil.copy2(source, app / name)
        Path(target).chmod(RUNNER_MODE)
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


def find_write_up() -> Path | None:
    """The optional write-up, or None if nobody has written one yet.

    Found rather than derived, like the video: section 4.2 does not require it, and
    a submission has to be packageable long before it exists.
    """
    found = sorted(
        WRITE_UP_DIR / f"{WRITE_UP_STEM}{suffix}"
        for suffix in WRITE_UP_EXTENSIONS
        if (WRITE_UP_DIR / f"{WRITE_UP_STEM}{suffix}").is_file()
    )
    return found[0] if found else None


def copy_write_up(source: Path, destination: Path) -> Path:
    """Copy the write-up to the top of Optional_Items, where section 4.2 puts it."""
    target = destination / OPTIONAL_DIR_NAME / f"{WRITE_UP_STEM}{source.suffix.lower()}"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


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

    root = SUBMISSION_ROOT if root is None else Path(root)
    destination = root / team
    # Rebuilt from scratch every time, so a subsystem that was removed or renamed
    # cannot linger in the folder we send.
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    write_archive(ready, destination)
    missing_app = copy_app(destination)
    shipped = copy_checkpoints(ready, destination)
    optional = copy_optional(ready, destination)
    source = find_video()
    video = None if source is None else copy_video(source, destination)
    paper = find_write_up()
    write_up = None if paper is None else copy_write_up(paper, destination)

    print(f"packaged {len(ready)} of {len(SUBSYSTEMS)} subsystems: {', '.join(ready)}")
    print(f"  {PREDICTIONS_ARCHIVE_NAME}  {', '.join(PREDICTION_PATHS[s].name for s in ready)}")
    print(f"  {APP_DIR_NAME}/            {RUNNERS[0]}, {', '.join(APP_PACKAGES)}"
          + (f", models for {', '.join(shipped)}" if shipped else ""))
    if optional:
        print(f"  {OPTIONAL_DIR_NAME}/  {', '.join(optional)}")
    if write_up is not None:
        print(f"  {OPTIONAL_DIR_NAME}/{write_up.name}  from {paper.parent}")
    if video is not None:
        print(f"  {video.name}          from {source.parent}")

    print(f"\nsubmission folder: {destination}")

    outstanding = []
    if missing_app:
        outstanding.append(f"file not found, skipped: {', '.join(missing_app)}")
    if write_up is None:
        outstanding.append(
            "file not found, skipped: the write-up. Section 4.2 does not require one, "
            "but it is where the approach and the assumptions get read. Put "
            f"{WRITE_UP_STEM}.<{'|'.join(s.lstrip('.') for s in WRITE_UP_EXTENSIONS)}> "
            f"in {WRITE_UP_DIR} and run this again."
        )
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
        help=f"Where to build it (default {SUBMISSION_ROOT}).",
    )
    arguments = parser.parse_args()

    try:
        build(arguments.team, arguments.into)
    except (OSError, ValueError) as error:
        raise SystemExit(f"Packaging failed: {error}")


if __name__ == "__main__":
    main()
