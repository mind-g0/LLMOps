# Multi-stage Dockerfile for the HR CV review agent.
#
# Pre-build the embedding model cache locally and mount it at runtime:
#   python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"
#   docker run -v ~/.cache/huggingface:/models/huggingface ...
#
# Build:    docker build -t hr-ai-agent agent/
# Run:      docker run --rm -e BACKEND_API_BASE=http://... hr-ai-agent --cv-id <id> --job-id <id> --save

FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check --user -r requirements.txt

FROM python:3.12-slim

# System deps for PDF rendering, image processing, DOC->PDF conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

# Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Agent source code
COPY agent ./agent
COPY config ./config
COPY rag ./rag
COPY utils ./utils
COPY main.py .

# Mountable paths for external data:
#   /models/huggingface   — pre-cached sentence-transformers (SENTENCE_TRANSFORMERS_HOME)
#   /data/qdrant          — Qdrant embedded DB (QDRANT_PATH)
#   /data/tmp             — CV processing temp files (TMP_DIR)
#   /data/logs            — agent logs (LOG_DIR)
#   /data/result          — analysis output (RESULT_DIR)

ENV SENTENCE_TRANSFORMERS_HOME=/models/huggingface \
    HF_HOME=/models/huggingface \
    QDRANT_PATH=/data/qdrant \
    TMP_DIR=/data/tmp \
    LOG_DIR=/data/logs \
    RESULT_DIR=/data/result

RUN groupadd -r agent && useradd --no-log-init -r -g agent agent && \
    mkdir -p /data/tmp /data/logs /data/result /data/qdrant /models/huggingface && \
    chown -R agent:agent /app /data /models

USER agent

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "from config import settings; exit(0 if settings.BACKEND_API_BASE else 1)"

ENTRYPOINT ["python", "-m", "agent.main"]