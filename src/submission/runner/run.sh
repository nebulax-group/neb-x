#!/usr/bin/env bash
# Start the Train Condition Monitoring app. Creates .venv on the first run.
#
# This is the copy that ships inside the submission, where there is no repository
# around it: no install.sh to call, no data/, and the trained models already sitting
# under outputs/models/. Packaging puts it at the top of app/ and nothing else in
# there is meant to be run.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    echo "creating .venv (first run only) ..."
    python3 -m venv .venv
    ./.venv/bin/python -m pip install --upgrade pip --quiet
    echo "installing requirements ..."
    ./.venv/bin/python -m pip install -r requirements.txt --quiet
fi

echo "starting the app -- press Ctrl+C to stop"
exec ./.venv/bin/streamlit run src/app/main.py "$@"
