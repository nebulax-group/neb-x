#!/usr/bin/env bash
# Build the submission end to end: ask who we are, run every subsystem over its
# held-out test inputs, check what comes out, then package it into <team>/ at the
# repository root. That folder is the upload, with nothing wrapped around it.
#
# The prediction CSVs are always regenerated here and never reused. A file left in
# outputs/predictions/ by an earlier run or a browser download is stale by
# definition, so it is overwritten, and one whose subsystem could not run at all is
# discarded rather than submitted.
#
# The demo video comes from video/out/, where scripts/render.sh leaves it, and
# falls back to any recording dropped in video/.
#
# Stops if validation fails. A CSV that does not match the schema is scored
# as-is by the organisers, so it must never reach predictions.zip. Anything
# else that is missing, an unfinished subsystem and the demo video included, is
# reported and skipped.
#
# Pass --team "Your Name" to skip the prompt.
set -euo pipefail

cd "$(dirname "$0")"

TEAM_ARGS=()
if [[ " $* " != *" --team "* ]]; then
    if [ -t 0 ]; then
        # The folder must carry the registered name exactly; it is how the
        # organisers identify the submission, so it is asked for rather than guessed.
        read -r -p "Team name, exactly as registered: " TEAM
        if [ -n "${TEAM// /}" ]; then
            TEAM_ARGS=(--team "$TEAM")
        else
            echo "no name given, falling back to the placeholder"
        fi
    else
        echo "not a terminal, falling back to the placeholder team name"
    fi
    echo
fi

echo "== 1/3  generating prediction files =="
./scripts/generate.sh

echo
echo "== 2/3  validating prediction files =="
./scripts/validate.sh

echo
echo "== 3/3  packaging the submission =="
./scripts/package.sh ${TEAM_ARGS[@]+"${TEAM_ARGS[@]}"} "$@"
