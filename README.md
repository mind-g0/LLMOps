# LLMOps Gateway

FastAPI gateway for the HR AI platform. It routes requests to the configured LLM
or OCR backend, discovers the available LLM model automatically, supports token
streaming, and persists CV review results in PostgreSQL and MinIO.

The RAG pipeline is intentionally not implemented in this repository yet. The
handoff contract for the RAG team is documented in
[RAG_INTEGRATION.md](RAG_INTEGRATION.md).

## Architecture

```text
Frontend
   |
   v
FastAPI gateway :8004
   |-- LLM backend (authenticated)
   |-- OCR backend
   |-- PostgreSQL: review metadata and decisions
   `-- MinIO: original CV files
```

## Repository Structure

```text
LLMOps/
|-- app/                    Backend application
|   |-- main.py             FastAPI entrypoint and app lifecycle
|   |-- gateway.py          LLM/OCR proxy and token streaming
|   |-- db.py               Async PostgreSQL connection
|   |-- models.py           SQLAlchemy ORM models
|   |-- reviews.py          CV review persistence endpoints
|   |-- storage.py          MinIO connection and CV uploads
|   `-- schemas.py           API request schemas
|-- frontend/               Static chat frontend
|   |-- index.html
|   |-- styles.css
|   `-- app.js
|-- manifest/               Kubernetes manifests and team material
|-- docker-compose.yml      Local PostgreSQL, MinIO, and supporting services
|-- Dockerfile              Backend container image
|-- requirements.txt        Python dependencies
|-- .env.example            Configuration template
|-- README.md               Repository overview and setup
`-- RAG_INTEGRATION.md      RAG team handoff contract
```

### Current Request Flow

```text
Client
  |
  | POST /v1/chat/completions
  v
app/main.py
  |
  v
app/gateway.py
  |-- task_type = llm -> configured LLM backend
  `-- task_type = ocr -> configured OCR backend
```

For an LLM request, the gateway discovers the available model automatically,
adds the backend authentication header, and either returns the complete response
or streams SSE chunks when `payload.stream` is true.

### Current CV Persistence Flow

```text
CV file + approval decision
  |
  v
POST /api/v1/cv-reviews
  |-- app/storage.py -> original CV in MinIO
  `-- app/models.py  -> decision metadata in PostgreSQL
```

The current repository stores review results, but it does not perform OCR,
embeddings, retrieval, or HR evaluation yet.

## Planned RAG Structure

The RAG team will add the RAG pipeline under `app/rag/`. This keeps RAG logic
separate from the gateway, database, and MinIO integrations that already exist.

```text
app/rag/
|-- __init__.py
|-- pipeline.py       Main CV analysis orchestration
|-- schemas.py        Validated RAG input and output models
|-- prompts.py        HR evaluation prompts and output instructions
|-- extractor.py      PDF/DOCX text extraction and OCR calls
|-- chunker.py        Splitting CV and HR documents into chunks
|-- embeddings.py     Embedding model client
|-- retriever.py      Vector search and HR context retrieval
`-- evaluator.py      LLM evaluation and structured decision parsing
```

The planned RAG flow is:

```text
CV upload
  -> extract text
  -> split text into chunks
  -> create embeddings
  -> retrieve HR requirements
  -> ask the LLM for a structured decision
  -> validate the decision
  -> save CV through /api/v1/cv-reviews
```

The RAG pipeline should expose one clear application-level function:

```python
async def analyze_cv(cv_bytes: bytes, filename: str) -> CVDecision:
    ...
```

It must return:

```json
{
  "approved": false,
  "rejection_reason": "Missing required experience"
}
```

The RAG team owns extraction, chunking, embeddings, retrieval, prompts, and
decision generation. It should use the existing gateway for model calls and the
existing CV review endpoint for persistence. It should not create duplicate
PostgreSQL or MinIO connection code.

See [RAG_INTEGRATION.md](RAG_INTEGRATION.md) for the complete handoff contract.

## Requirements

- Python 3.12+
- Docker and Docker Compose
- PostgreSQL
- MinIO
- A configured LLM backend with an OpenAI-compatible API

## Configuration

Copy the example environment file and fill in real values:

```bash
cp .env.example .env
```

Never commit `.env` or API keys.

Important variables:

```env
MODEL_LLM_URL=https://llm.example.com/v1/chat/completions
MODEL_OCR_URL=http://localhost:8002/v1/chat/completions
LLM_API_KEY=your-llm-api-key
DATABASE_URL=postgresql+asyncpg://llmops:password@localhost:5432/llmops
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=your-minio-password
MINIO_BUCKET=cv-files
MINIO_SECURE=false
CORS_ALLOW_ORIGINS=http://localhost:5500,http://127.0.0.1:5500
```

All variables above are required. The application does not provide fallback
values for database, MinIO, model, or CORS configuration.

## Local Setup

Install Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Start PostgreSQL and MinIO:

```bash
docker compose up -d postgres llmops-s3
```

Start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8004
```

The application creates the `cv_reviews` table during startup. Production
deployments should use database migrations instead of automatic table creation.

Check the gateway:

```bash
curl http://localhost:8004/health
```

Expected response:

```json
{ "status": "healthy" }
```

## LLM Gateway

The public gateway endpoint is:

```text
POST /v1/chat/completions
```

The client selects the backend with `task_type`. The gateway selects the model
from the LLM backend's `/v1/models` endpoint when `model` is not supplied.

Non-streaming request:

```bash
curl -X POST http://localhost:8004/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "llm",
    "payload": {
      "stream": false,
      "messages": [
        {"role": "user", "content": "Hello"}
      ],
      "max_tokens": 50
    }
  }'
```

Streaming request:

```bash
curl -N -X POST http://localhost:8004/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "llm",
    "payload": {
      "stream": true,
      "messages": [
        {"role": "user", "content": "Explain Kubernetes briefly."}
      ],
      "max_tokens": 100
    }
  }'
```

The gateway adds the configured LLM key as an internal Bearer token. Clients do
not send the LLM key to the gateway.

## CV Review Persistence

Create a review record and upload the original CV:

```bash
curl -X POST http://localhost:8004/api/v1/cv-reviews \
  -F "cv=@candidate.pdf" \
  -F "approved=false" \
  -F "rejection_reason=Missing required experience"
```

Endpoints:

```text
POST /api/v1/cv-reviews       Upload CV and save decision
GET  /api/v1/cv-reviews       List saved reviews
GET  /api/v1/cv-reviews/{id}  Get one review
```

Each review stores the CV name, approval decision, rejection reason, MinIO
object key, UUID, and creation time in PostgreSQL. The original CV is stored in
MinIO under `cvs/<review-id>/<filename>`.

`rejection_reason` is optional because the RAG decision format is still subject
to human review. Approved and rejected records may both store a null reason.

## Frontend

Start the static chat frontend in a second terminal:

```bash
python -m http.server 5500 --directory frontend
```

Open:

```text
http://localhost:5500
```

The frontend sends streaming requests to the gateway at port `8004`.

## RAG Integration

The RAG team owns OCR, extraction, chunking, embeddings, retrieval, HR context,
and decision generation. LLMOps owns model proxying, PostgreSQL, MinIO, and
review persistence.

Read [RAG_INTEGRATION.md](RAG_INTEGRATION.md) for the required decision schema,
team responsibilities, and integration examples.

## Validation

Compile the Python application:

```bash
python -m py_compile app/*.py
```

Check the API health endpoint after starting the server:

```bash
curl http://localhost:8004/health
```
