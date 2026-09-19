#!/usr/bin/env bash
# Thin wrapper: fit the rail corrugation classifier, creating or refreshing .venv first.
# See src/rail/train.py.
set -euo pipefail

cd "$(dirname "$0")/.."

STAMP=".venv/.requirements-sha"

if [ ! -d .venv ]; then
    echo "no .venv yet -- running ./install.sh"
    ./install.sh
fi

# A Windows venv puts activate under Scripts/ rather than bin/.
ACTIVATE=".venv/bin/activate"
[ -f "$ACTIVATE" ] || ACTIVATE=".venv/Scripts/activate"
# shellcheck disable=SC1091
source "$ACTIVATE"

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

echo
# Pass --refresh through to re-extract the feature cache, which is mandatory after
# editing features.py; the module owns that default, not this script. Expect ~390 s
# with a refresh and ~230 s without one.
exec python -m src.rail.train "$@"
