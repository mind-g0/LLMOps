# Simple single-stage Dockerfile for the HR CV review agent.
#
# Build:  docker build -t hr-ai-agent agent/
# Pre-load the embedding model: see agent/.env.example
#
# Run (process all pending CVs once):
#   docker run --rm \
#     -e BACKEND_API_BASE=http://... \
#     -e LLM_API_BASE=http://.../v1 \
#     -e VLM_API_BASE=http://.../v1 \
#     -e LLM_API_KEY=*** \
#     -v /home/nassir/models/:/models/huggingface \
#     hr-ai-agent --once
#
# Run (watch daemon):
#   docker run --rm -d --restart=always \
#     -e BACKEND_API_BASE=http://... \
#     ... same env vars ... \
#     --name hr-ai-agent \
#     hr-ai-agent --watch --interval 30

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 poppler-utils libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

COPY agent ./agent
COPY analysis ./analysis
COPY config ./config
COPY rag ./rag
COPY utils ./utils
COPY main.py .

ENV SENTENCE_TRANSFORMERS_HOME=/models/huggingface \
    HF_HOME=/models/huggingface \
    HOME=/home/agent \
    DSPY_CACHE_DIR=/data/dspy_cache \
    QDRANT_PATH=/data/qdrant \
    TMP_DIR=/data/tmp \
    LOG_DIR=/data/logs \
    RESULT_DIR=/data/result \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd -r agent && useradd --no-log-init -r -g agent agent && \
    mkdir -p /data/tmp /data/logs /data/result /data/qdrant /data/dspy_cache /models/huggingface /home/agent && \
    chown -R agent:agent /app /data /models /home/agent

USER agent

ENTRYPOINT ["python", "main.py"]