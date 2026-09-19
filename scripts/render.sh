#!/usr/bin/env bash
# Thin wrapper: render the pitch video, creating or refreshing .venv first.
# See src/video/render.py.
set -euo pipefail

cd "$(dirname "$0")/.."

STAMP=".venv/.requirements-sha"
VIDEO_STAMP=".venv/.video-requirements-sha"

if [ ! -d .venv ]; then
    echo "no .venv yet -- running ./install.sh"
    ./install.sh
fi

# shellcheck disable=SC1091
source .venv/bin/activate

WANT="$(python -c "import hashlib, pathlib; print(hashlib.sha256(pathlib.Path('requirements.txt').read_bytes()).hexdigest())")"
HAVE="$(cat "$STAMP" 2>/dev/null || true)"

# Reinstall when requirements.txt has moved since the last run, so a teammate adding a
# dependency does not leave everyone else on a stale venv that fails at import time.
if [ "$WANT" != "$HAVE" ] || ! python -c "import pandas, numpy" >/dev/null 2>&1; then
    echo "installing requirements ..."
    python -m pip install -r requirements.txt --quiet
    printf '%s' "$WANT" >"$STAMP"
else
    echo "requirements already satisfied"
fi

# manim is kept out of requirements.txt on purpose: it needs cairo, pango and ffmpeg,
# and everyone installs that file, the deployed app included. Only this script installs
# video/requirements.txt, and only on the machine that renders.
VIDEO_WANT="$(python -c "import hashlib, pathlib; print(hashlib.sha256(pathlib.Path('video/requirements.txt').read_bytes()).hexdigest())")"
VIDEO_HAVE="$(cat "$VIDEO_STAMP" 2>/dev/null || true)"

if [ "$VIDEO_WANT" != "$VIDEO_HAVE" ] || ! python -c "import manim" >/dev/null 2>&1; then
    echo "installing the render requirements ..."
    python -m pip install -r video/requirements.txt --quiet
    printf '%s' "$VIDEO_WANT" >"$VIDEO_STAMP"
else
    echo "render requirements already satisfied"
fi

echo

# Arguments mean the caller has already chosen, and --help must not sit behind a prompt.
if [ "$#" -gt 0 ]; then
    exec python -m src.video.render "$@"
fi

read -r QUALITY FPS <<<"$(python -m src.video.render --defaults)"

if [ -t 0 ]; then
    read -r -p "manim quality [$QUALITY]: " ANSWER
    if [ -n "${ANSWER// /}" ]; then
        QUALITY="$ANSWER"
    fi
    read -r -p "frames per second [$FPS]: " ANSWER
    if [ -n "${ANSWER// /}" ]; then
        FPS="$ANSWER"
    fi
    echo
else
    echo "not a terminal, rendering at $QUALITY and $FPS fps"
fi

# The module decides what is rendered, in what order and how it is stitched.
exec python -m src.video.render --quality "$QUALITY" --fps "$FPS"
