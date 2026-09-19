# Cloud Run image for the compulsory app. The models under outputs/models/ are baked in
# (1.3 MB total), so a cold container serves a prediction without any training step.
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first so a code change does not reinstall them.
COPY scripts/requirements.txt scripts/requirements.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install -r scripts/requirements.txt

COPY .streamlit/ .streamlit/
COPY src/ src/
COPY reference/ reference/
COPY docs/ docs/
COPY outputs/models/ outputs/models/

# Cloud Run injects PORT; Streamlit must bind it on every interface, not localhost.
ENV PORT=8080
EXPOSE 8080
CMD exec streamlit run src/app/main.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.maxUploadSize=1024 \
    --browser.gatherUsageStats=false
