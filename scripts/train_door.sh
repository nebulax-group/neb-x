#!/usr/bin/env bash
# Thin wrapper: fit the Door classifier, creating or refreshing .venv first.
# See src/door/train.py.
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
if [ "$WANT" != "$HAVE" ] || ! python -c "import sklearn, joblib, pandas, numpy" >/dev/null 2>&1; then
    echo "installing requirements ..."
    python -m pip install -r scripts/requirements.txt --quiet
    printf '%s' "$WANT" >"$STAMP"
else
    echo "requirements already satisfied"
fi

echo
# Reports cross-validated accuracy, then writes the checkpoint under outputs/models/door/.
# The module decides where and what it prints, not this script.
exec python -m src.door.train "$@"
