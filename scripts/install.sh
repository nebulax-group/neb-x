#!/usr/bin/env bash
# Bootstrap the one virtualenv for neb-x. Safe to re-run.
#
# Lives beside the wrappers that call it, but .venv belongs to the repository
# rather than to scripts/, so this runs from the root like every other wrapper.
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"

command -v "$PYTHON" >/dev/null 2>&1 || {
    echo "error: '$PYTHON' not found. Install Python 3.12+ and re-run." >&2
    echo "       Override the interpreter with: PYTHON=python3.12 ./scripts/install.sh" >&2
    exit 1
}

"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 12):
    sys.exit(f"error: Python 3.12+ required, found {sys.version.split()[0]}")
PY

if [ ! -d .venv ]; then
    echo "creating .venv ..."
    "$PYTHON" -m venv .venv
else
    echo ".venv already exists, reusing it"
fi

# Call the venv's interpreter directly rather than activating: this script runs in a
# subshell, so an activation here would not survive back to the caller anyway.
VENV_PY=".venv/bin/python"

"$VENV_PY" -m pip install --upgrade pip --quiet
"$VENV_PY" -m pip install -r scripts/requirements.txt

"$VENV_PY" - <<'PY'
import importlib, sys
failed = []
for name in ("numpy", "scipy", "pandas", "openpyxl", "sklearn", "streamlit"):
    try:
        mod = importlib.import_module(name)
        print(f"  ok    {name:14s} {getattr(mod, '__version__', '?')}")
    except Exception as exc:
        failed.append(name)
        print(f"  FAIL  {name:14s} {type(exc).__name__}: {exc}")
if failed:
    sys.exit(f"error: {len(failed)} package(s) installed but will not import: {', '.join(failed)}")
PY

echo
echo "Done. Activate it in your shell with:"
echo "    source .venv/bin/activate"
