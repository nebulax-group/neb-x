#!/usr/bin/env bash
# Build the submission end to end: ask who we are, check the prediction files,
# then package them into outputs/submission/<team>/.
#
# Stops if validation fails. A CSV that does not match the schema is scored
# as-is by the organisers, so it must never reach predictions.zip. Anything
# else that is missing, the demo video included, is reported and skipped.
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

echo "== 1/2  validating prediction files =="
./scripts/validate.sh

echo
echo "== 2/2  packaging the submission =="
./scripts/package.sh ${TEAM_ARGS[@]+"${TEAM_ARGS[@]}"} "$@"
