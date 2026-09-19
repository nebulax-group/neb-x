#!/usr/bin/env bash
# Thin wrapper: start the app, creating or refreshing .venv first. See src/app/main.py.
set -euo pipefail

cd "$(dirname "$0")/.."

STAMP=".venv/.requirements-sha"

if [ ! -d .venv ]; then
    echo "no .venv yet -- running ./scripts/install.sh"
    ./scripts/install.sh
fi

# shellcheck disable=SC1091
source .venv/bin/activate

WANT="$(python -c "import hashlib, pathlib; print(hashlib.sha256(pathlib.Path('scripts/requirements.txt').read_bytes()).hexdigest())")"
HAVE="$(cat "$STAMP" 2>/dev/null || true)"

# Reinstall when requirements.txt has moved since the last run, so a teammate adding a
# dependency does not leave everyone else on a stale venv that fails at import time.
if [ "$WANT" != "$HAVE" ] || ! python -c "import streamlit, pandas, numpy" >/dev/null 2>&1; then
    echo "installing requirements ..."
    python -m pip install -r scripts/requirements.txt --quiet
    printf '%s' "$WANT" >"$STAMP"
else
    echo "requirements already satisfied"
fi

echo "starting the app -- press Ctrl+C to stop"
exec streamlit run src/app/main.py "$@"
