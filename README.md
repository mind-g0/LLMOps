# LLMOps — HR AI Platform v1.0.0

End-to-end HR AI platform: upload CVs, match against job requirements, and
receive structured evaluation reports with skill-gap analysis and learning
recommendations.

```
                 ┌──────────────┐
                 │   Frontend   │  React + Vite + Tailwind
                 │  :5500/:6661 │
                 └──────┬───────┘
                        │ /v1/chat/completions  /api/v1/cv-reviews
                        v
            ┌───────────────────────┐
            │  FastAPI Gateway      │  Port 8004
            │  app/                  │
            │  - gateway.py (proxy)  │  LLM + OCR routing
            │  - reviews.py (CRUD)   │  CV persistence
            │  - jobs.py (jobs)      │  Job requirement CRUD
            │  - storage.py (MinIO)  │  CV file storage
            └───────┬───────┬───────┘
                    │       │
                    v       v
        ┌───────────────────┐  ┌────────────────┐
        │   LangGraph Agent │  │  Qdrant        │
        │   agent/          │  │  :6323         │
        │   CV analysis     │  │  Vector store   │
        │   pipeline        │  │  Job embeddings │
        └───────────────────┘  └────────────────┘
                    │
                    v
        ┌───────────────────┐
        │   PostgreSQL      │  MinIO (S3)
        │   :5432           │  :9000
        │   Review metadata │  CV files
        └───────────────────┘
```

## Repository Structure

```
LLMOps/
├── app/                    FastAPI backend (gateway, reviews, jobs)
│   ├── main.py             Entrypoint, CORS, router setup
│   ├── gateway.py          LLM/OCR proxy + token streaming
│   ├── reviews.py          CV review CRUD + file upload
│   ├── jobs.py             Job requirement CRUD
│   ├── db.py               Async PostgreSQL
│   ├── models.py           SQLAlchemy ORM
│   ├── schemas.py          Pydantic schemas
│   └── storage.py          MinIO client
├── agent/                  LangGraph CV evaluation pipeline
│   ├── main.py             Poll/event-driven entrypoints (+ CLI)
│   ├── agent/              Graph nodes (retriever → converter → parser → extractor → validator → gap → matcher → recommender → formatter)
│   ├── rag/                Vector store utils (embedder, store, job_ingest, bulk, sync_job)
│   ├── config/             Settings and tunable parameters
│   ├── analysis/           Scoring rules and skill matching
│   ├── tests/              Pytest suite (24 deterministic tests, no GPU)
│   ├── cv_data/            Sample CVs
│   └── data/               Job postings
├── frontend/               React + Vite + Tailwind + i18n (EN/AR)
│   ├── src/                Components, pages, locales, API layer
│   └── Dockerfile          Nginx-served production build
├── manifest/               K8s Helm charts + team configs
│   ├── team-llmops/        vLLM, agent, backend, frontend charts
│   ├── nassir/             Per-developer overlays
│   ├── salman/
│   └── yaser/
├── eval/                   Parsing benchmarks and evaluation results
├── docker-compose.yml      Local dev stack (7 services)
├── Dockerfile              Backend container image
├── requirements.txt        Python dependencies
└── .env.example            Configuration template
```

## Agent Pipeline

```
START → retriever → converter → parser → extractor → validator
                                                        │
                          ┌─────────────────────────────┘
                          v
                    gap (ReAct) → matcher → recommender (ReAct) → formatter
```

| Node       | LLM?               | Notes |
|------------|--------------------|-------|
| retriever  | no                 | Job loaded by `job_id` payload; fails fast if missing |
| converter  | no                 | File→image conversion (PDF/DOCX pages) |
| parser     | no                 | Text parsing from Docling + page images |
| extractor  | Qwen3-VL           | Vision-first for every PDF/DOCX; values kept in original language |
| validator  | no                 | Grounding checks (skills/name must exist in document), confidence |
| gap        | Qwen3.5 thinking   | ReAct: skill-gap analysis with CV search + job context |
| matcher    | Qwen3.5            | Score from rubric + triage; enum verdicts |
| recommender| Qwen3.5 + Tavily   | ReAct: learning resource recommendations from real search |
| formatter  | no                 | JSON + localised markdown (EN/AR); always emits a report |

## Services (Docker Compose)

| Service      | Image                        | Port(s)     | Purpose |
|--------------|------------------------------|-------------|---------|
| postgres     | postgres:16                  | 5432        | Review metadata + job requirements |
| llmops-s3    | minio/minio                  | 9000, 9001  | CV file storage |
| qdrant       | qdrant/qdrant                | 6323, 6324  | Vector store (job embeddings, CV index) |
| redis        | redis:alpine                 | 6379        | Event queue for agent CV processing |
| cloudbeaver  | dbeaver/cloudbeaver          | 8978        | Database GUI |
| node_exporter| prometheus/node-exporter     | host        | System metrics |
| agent        | agent (local build)          | host        | LangGraph CV analysis daemon |

## Configuration

Copy and fill:

```bash
cp .env.example .env
```

Key variables:

```env
# Docker Compose credentials
S3_ROOT_PASSWORD=...
DB_PASSWORD=...
QDRANT_API_KEY=...

# LLM / OCR backends (K8s cluster URLs)
MODEL_LLM_BASE_URL=http://<k8s-svc>:8000/v1
MODEL_OCR_BASE_URL=http://<k8s-svc>:8001/v1
LLM_API_KEY=...

# Database / storage
DATABASE_URL=postgresql+asyncpg://llmops:<pw>@<host>:5432/llmops
MINIO_ENDPOINT=<minio-host>/
MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...
MINIO_BUCKET=cv-files
MINIO_SECURE=true

# CORS
CORS_ALLOW_ORIGINS=https://llmops.example.com,https://llmops-front.example.com

# Redis (event-driven agent)
REDIS_HOST=172.17.0.1

# Agent settings
LM_TIMEOUT=600
TAVILY_API_KEY=tvly-...
```

All variables above are required. The application does not provide fallback
values.

## Setup

### Backend + infrastructure

```bash
docker compose up -d postgres llmops-s3 qdrant redis cloudbeaver

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8004
```

Check health:

```bash
curl http://localhost:8004/health
# {"status": "healthy"}
```

### Agent (LangGraph CV evaluation)

```bash
cd agent
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.lock

# Ingest job postings into Qdrant
python -m rag.job_ingest --dir data

# Process a single CV
python main.py --cv cv_data/doc_0001.pdf --job-id backend_engineer

# Process all pending CVs (daemon mode)
python main.py --watch

# Bulk evaluation
python -m rag.bulk --cv-dir cv_data --job-id backend_engineer --top-k 50
```

### Agent (Docker)

```bash
sudo docker build --no-cache -t agent ./agent
sudo docker run -d --name llmops-agent \
  --restart unless-stopped \
  --network host \
  -v /home/nassir/models/hf/:/models/huggingface \
  --env-file .env \
  agent --watch
```

Scale horizontally — run multiple containers; Redis distributes CVs atomically.

### Frontend

```bash
cd frontend
npm install
npm run dev       # dev mode
npm run build     # production build → dist/
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/health` | Health check |
| POST   | `/v1/chat/completions` | LLM/OCR gateway (streaming supported) |
| POST   | `/api/v1/cv-reviews` | Upload CV + save decision |
| GET    | `/api/v1/cv-reviews` | List saved reviews |
| GET    | `/api/v1/cv-reviews/{id}` | Get single review |
| GET    | `/api/v1/cv-reviews/{id}/file-content` | Download CV file |
| PATCH  | `/api/v1/cv-reviews/{id}` | Update review (agent writes results here) |
| POST   | `/api/v1/jobs` | Create job requirement |
| GET    | `/api/v1/jobs` | List job requirements |
| POST   | `/api/v1/jobs/sync` | Sync jobs to Qdrant |
| DELETE | `/api/v1/jobs/{id}` | Delete job requirement |

## Deployment (K3s)

Helm charts in `manifest/team-llmops/`:

- `vLLM-OCR-chart/` — Qwen3-VL OCR serving (FP8, time-sliced GPU)
- `vLLM-LLM-chart/` — Qwen3.5-9B text LLM
- `agent-chart/` — LangGraph agent
- `backend-chart/` — FastAPI gateway
- `frontend-chart/` — React SPA (Nginx)
- `qdrant-chart/` — Vector store
- `monitoring-stack/` — Prometheus + Grafana

Single GPU time-sliced into 2 replicas via NVIDIA device plugin. Both models
(~14G + ~16G VRAM) fit on a 48 GB RTX A6000.

## Architecture Decisions

- **Vision-first extraction** — every PDF/DOCX goes through the VLM (not just
  text failures), catching tables and layout-only content.
- **Event-driven agent** — Redis queue replaces polling for scalable CV
  processing; multiple agent containers consume from the same queue.
- **Two-agent ReAct loops** — gap analysis and learning recommendations each
  use bounded tool-use iterations (3 rounds max) for latency control.
- **No PII in search** — Tavily calls from recommender send skill names only,
  never candidate names or contact info.

## Team

Team 4 — Beamdata capstone project. Active branches: `develop`, `main`, and
per-developer branches (`nassir`, `yaser`, `salman`, `Rag`).