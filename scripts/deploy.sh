#!/usr/bin/env bash
# Thin wrapper: build the Dockerfile at the repo root with Cloud Build and serve it on
# Cloud Run. Prints the public URL. Requires an already-authenticated gcloud.
set -euo pipefail

cd "$(dirname "$0")/.."

SERVICE="${SERVICE:-neb-x}"
REGION="${REGION:-asia-southeast1}"

PROJECT="$(gcloud config get-value project 2>/dev/null)"
if [ -z "$PROJECT" ] || [ "$PROJECT" = "(unset)" ]; then
    echo "no project set -- run: gcloud config set project <PROJECT_ID>" >&2
    exit 1
fi

gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# One instance, kept warm: Streamlit holds session state in the process, so a second
# instance would drop a judge mid-upload. 4 GiB because a rail file is 17 MB of CSV.
gcloud run deploy "$SERVICE" \
    --source . \
    --region "$REGION" \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --timeout 3600 \
    --min-instances 1 \
    --max-instances 1 \
    --session-affinity

gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)'
