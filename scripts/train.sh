#!/usr/bin/env bash
# Thin wrapper: fit every subsystem that has a trainer, in one pass.
#
# One run leaves outputs/models/ complete, which is what ./submit.sh assumes and
# does not do for itself. Each subsystem runs as its own process, so one whose
# data is absent on this machine costs only itself and the rest still fit.
#
# Takes no arguments on purpose: --refresh means something to rail and is an error
# everywhere else. The per-subsystem wrappers are where their own flags go.
# Expect rail to dominate the wall clock: ~60 s against a warm feature cache under
# outputs/models/rail/, ~390 s the first time on a machine, when it extracts one.
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
if [ "$WANT" != "$HAVE" ] || ! python -c "import sklearn, joblib, pandas, numpy" >/dev/null 2>&1; then
    echo "installing requirements ..."
    python -m pip install -r scripts/requirements.txt --quiet
    printf '%s' "$WANT" >"$STAMP"
else
    echo "requirements already satisfied"
fi

# Asked for rather than restated here: config owns which subsystems exist, and one
# is trainable exactly when it ships a train.py -- the same way the app decides what
# it can predict. A new subsystem joins this run by existing.
SUBSYSTEMS="$(python -c "from src.common.config import SUBSYSTEMS; print(*SUBSYSTEMS)")"
# An empty list would train nothing and say so in a summary that reads like success,
# which is the one outcome this script must never produce quietly.
[ -n "$SUBSYSTEMS" ] || {
    echo "error: no subsystems to train; src/common/config.py listed none" >&2
    exit 1
}

TRAINED=""
UNTRAINED=""
FAILED=""

for SUBSYSTEM in $SUBSYSTEMS; do
    if [ ! -f "src/$SUBSYSTEM/train.py" ]; then
        UNTRAINED="$UNTRAINED $SUBSYSTEM"
        continue
    fi
    echo
    echo "== $SUBSYSTEM =="
    if python -m "src.$SUBSYSTEM.train"; then
        TRAINED="$TRAINED $SUBSYSTEM"
    else
        FAILED="$FAILED $SUBSYSTEM"
    fi
done

echo
[ -z "$TRAINED" ] || echo "trained:$TRAINED"
# ACV is the one that lands here: its ranking fits no parameters, so it has nothing
# to train and is ready to predict without this step.
[ -z "$UNTRAINED" ] || echo "no trainer, nothing to fit:$UNTRAINED"
if [ -n "$FAILED" ]; then
    echo "failed:$FAILED" >&2
    exit 1
fi
