#!/usr/bin/env bash
# Thin wrapper: verify this machine's environment. See scripts/check_env.py.
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/python scripts/check_env.py "$@"
