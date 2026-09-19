"""Render every scene in video/src/ and stitch them into one pitch video.

Run as ``python -m src.video.render [--quality qh] [--fps 60]``.

Scenes render in filename order, so the two-digit prefix on each file is the
running order of the cut. The result is written to ``video/out/`` under the name
the submission expects, and ``src/submission/package.py`` copies it from there.

manim is deliberately absent from the root ``requirements.txt``: it needs cairo,
pango and a system ffmpeg, and everyone installs that file, the deployed app
included. It lives in ``video/requirements.txt``, which ``scripts/render.sh``
installs on top.
"""

import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

from src.common.config import (
    DEMO_VIDEO_STEM,
    VIDEO_MEDIA_DIR,
    VIDEO_OUT_DIR,
    VIDEO_REQUIREMENTS_PATH,
    VIDEO_SRC_DIR,
)

DEFAULT_QUALITY = "qh"
DEFAULT_FPS = 60

# manim's own flag spellings, so the prompt asks for exactly what a manim user types.
QUALITY_CHOICES = ("ql", "qm", "qh", "qp", "qk")

OUTPUT_FORMAT = "mp4"
FFMPEG = "ffmpeg"

# manim's layout under --media_dir: videos/<scene file stem>/<resolution>/<Scene>.mp4,
# with its animation cache in a partial_movie_files/ folder alongside them.
MANIM_VIDEO_SUBDIR = "videos"
PARTIAL_MOVIE_SUBDIR = "partial_movie_files"
CONCAT_LIST_NAME = "clips.txt"


def scene_files() -> list[Path]:
    """Every scene source, in the order they are cut together."""
    if not VIDEO_SRC_DIR.is_dir():
        raise FileNotFoundError(f"No scene folder at {VIDEO_SRC_DIR}.")

    found = sorted(
        path for path in VIDEO_SRC_DIR.glob("*.py") if not path.name.startswith("_")
    )
    if not found:
        raise FileNotFoundError(f"No scenes to render in {VIDEO_SRC_DIR}.")
    return found


def require_tools() -> None:
    """Refuse to start without manim and ffmpeg, naming how to install each."""
    if importlib.util.find_spec("manim") is None:
        raise RuntimeError(
            "manim is not installed in this environment. Run scripts/render.sh, which "
            f"installs it, or `python -m pip install -r {VIDEO_REQUIREMENTS_PATH}`."
        )
    if shutil.which(FFMPEG) is None:
        raise RuntimeError(
            "ffmpeg is not on PATH. manim renders through it and the scenes are "
            "stitched with it. Install it with `winget install Gyan.FFmpeg` on "
            "Windows, `brew install ffmpeg` on macOS, or `apt install ffmpeg` on Linux."
        )


def clips_of(scene: Path) -> list[Path]:
    """The finished clips manim has written for one scene file."""
    rendered = VIDEO_MEDIA_DIR / MANIM_VIDEO_SUBDIR / scene.stem
    if not rendered.is_dir():
        return []
    return sorted(
        path
        for path in rendered.rglob(f"*.{OUTPUT_FORMAT}")
        if PARTIAL_MOVIE_SUBDIR not in path.parts
    )


def render_scene(scene: Path, quality: str, fps: int) -> list[Path]:
    """Render one scene file and return the clips it produced."""
    # Clearing the finished clips first means a renamed or deleted Scene class cannot
    # be stitched into the cut from a previous run. The cache beside them is left
    # alone, so re-rendering an unchanged scene stays cheap.
    for stale in clips_of(scene):
        stale.unlink()

    command = [
        sys.executable,
        "-m",
        "manim",
        "render",
        f"-{quality}",
        "--fps",
        str(fps),
        "--format",
        OUTPUT_FORMAT,
        "--media_dir",
        str(VIDEO_MEDIA_DIR),
        "--write_all",
        str(scene),
    ]
    if subprocess.run(command).returncode != 0:
        raise RuntimeError(f"manim failed on {scene.name}. Its output is above.")

    clips = clips_of(scene)
    if not clips:
        raise RuntimeError(
            f"{scene.name} rendered no video. A scene whose construct is still empty "
            "produces nothing; write it or take the file out of video/src/."
        )
    return clips


def stitch(clips: list[Path], destination: Path) -> Path:
    """Concatenate the clips into one file without re-encoding them."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    VIDEO_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    listing = VIDEO_MEDIA_DIR / CONCAT_LIST_NAME
    listing.write_text(
        "".join(f"file '{clip.as_posix()}'\n" for clip in clips), encoding="utf-8"
    )

    # Stream copy rather than re-encode: every clip came from the same manim run, so
    # they already share a codec, a resolution and a frame rate. A clip from anywhere
    # else needs this to re-encode instead, or the cut plays as the first clip only.
    command = [
        FFMPEG,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(listing),
        "-c",
        "copy",
        str(destination),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"ffmpeg could not stitch the scenes.\n{completed.stderr.strip()}")
    return destination


def render(quality: str = DEFAULT_QUALITY, fps: int = DEFAULT_FPS) -> Path:
    """Render every scene and stitch them, returning the finished video."""
    if quality not in QUALITY_CHOICES:
        raise ValueError(
            f"quality must be one of {', '.join(QUALITY_CHOICES)}, not {quality!r}."
        )
    if fps <= 0:
        raise ValueError(f"fps must be a positive whole number, not {fps!r}.")

    require_tools()
    scenes = scene_files()

    clips: list[Path] = []
    for position, scene in enumerate(scenes, start=1):
        print(f"\n== {position}/{len(scenes)}  {scene.name}  ({quality}, {fps} fps) ==")
        clips.extend(render_scene(scene, quality, fps))

    destination = stitch(clips, VIDEO_OUT_DIR / f"{DEMO_VIDEO_STEM}.{OUTPUT_FORMAT}")

    print(f"\nstitched {len(clips)} clip(s) from {len(scenes)} scene(s)")
    print(f"pitch video: {destination}")
    print("./submit.sh copies it into the submission as the demo video.")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Render and stitch the pitch video.")
    parser.add_argument(
        "--quality",
        default=DEFAULT_QUALITY,
        help=f"manim quality flag, one of {', '.join(QUALITY_CHOICES)} (default {DEFAULT_QUALITY}).",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=DEFAULT_FPS,
        help=f"Frames per second (default {DEFAULT_FPS}).",
    )
    # Read by scripts/render.sh and render.bat so the prompts can offer the defaults
    # without restating them.
    parser.add_argument(
        "--defaults",
        action="store_true",
        help="Print the default quality and fps, then exit.",
    )
    arguments = parser.parse_args()

    if arguments.defaults:
        print(f"{DEFAULT_QUALITY} {DEFAULT_FPS}")
        return

    try:
        render(arguments.quality, arguments.fps)
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"Render failed: {error}")


if __name__ == "__main__":
    main()
