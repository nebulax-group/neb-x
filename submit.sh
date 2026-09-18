#!/usr/bin/env bash
# Build the submission end to end: check the prediction files, then package them.
#
# Stops at the first failure on purpose. A CSV that does not match the schema is
# scored as-is by the organisers, so it must never reach predictions.zip.
#
# Pass --team "Your Name" to set the top-level folder name.
set -euo pipefail

cd "$(dirname "$0")"

echo "== 1/2  validating prediction files =="
./scripts/validate.sh

echo
echo "== 2/2  packaging the submission =="
./scripts/package.sh "$@"
