#!/usr/bin/env bash
# Thin wrapper: write every prediction CSV, creating or refreshing .venv first.
# See src/submission/generate.py.
set -euo pipefail

cd "$(dirname "$0")/.."

STAMP=".venv/.requirements-sha"

if [ ! -d .venv ]; then
    echo "no .venv yet -- running ./scripts/install.sh"
    ./scripts/install.sh
fi

# A Windows venv puts activate under Scripts/ rather than bin/.
ACTIVATE=".venv/bin/activate"
[ -f "$ACTIVATE" ] || ACTIVATE=".venv/Scripts/activate"
# shellcheck disable=SC1091
source "$ACTIVATE"

WANT="$(python -c "import hashlib, pathlib; print(hashlib.sha256(pathlib.Path('scripts/requirements.txt').read_bytes()).hexdigest())")"
HAVE="$(cat "$STAMP" 2>/dev/null || true)"

# Reinstall when requirements.txt has moved since the last run, so a teammate adding a
# dependency does not leave everyone else on a stale venv that fails at import time.
if [ "$WANT" != "$HAVE" ] || ! python -c "import pandas, numpy" >/dev/null 2>&1; then
    echo "installing requirements ..."
    python -m pip install -r scripts/requirements.txt --quiet
    printf '%s' "$WANT" >"$STAMP"
else
    echo "requirements already satisfied"
fi

echo
# Takes no arguments: a partial run would leave one subsystem's CSV older than the
# rest, which is the state this step exists to make impossible. The module decides.
exec python -m src.submission.generate
