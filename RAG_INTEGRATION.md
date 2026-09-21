# RAG Team Integration Guide

This document defines the contract between the HR RAG team and the LLMOps gateway.

The RAG team owns CV analysis. LLMOps owns model proxying, PostgreSQL persistence,
and MinIO file storage.

## Responsibilities

### RAG team owns

- CV text extraction and OCR integration
- Chunking and document preparation
- Embeddings and vector retrieval
- HR requirements and policy context
- Prompt design and model evaluation
- Producing a validated approval decision

### LLMOps owns

- Calling the configured LLM backend
- Automatic model discovery
- Streaming model responses
- PostgreSQL ORM and database connections
- MinIO connections and CV object storage
- Storing review decisions and rejection reasons
- Providing review records for the future frontend

Do not create a second PostgreSQL or MinIO integration in the RAG code.

## Required Decision Contract

After analyzing a CV, the RAG pipeline must produce this result:

```json
{
  "approved": false,
  "rejection_reason": "The candidate does not have the required Kubernetes experience."
}
```

Rules:

- `approved` is required and must be a boolean.
- `rejection_reason` is optional while the RAG decision format is under human review.
- `rejection_reason` may be `null` for either approval decision.
- The result must be validated before it is saved.
- Do not save free-form or partially parsed LLM output.

Recommended Pydantic model:

```python
from pydantic import BaseModel


class CVDecision(BaseModel):
    approved: bool
    rejection_reason: str | None = None
```

## Gateway Model Request

The gateway endpoint is:

```text
POST /v1/chat/completions
```

The client does not need to choose a model. The gateway discovers the available
model from the backend and adds the model ID automatically.

Example request:

```bash
curl -N -X POST http://localhost:8004/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "llm",
    "payload": {
      "stream": false,
      "messages": [
        {
          "role": "system",
          "content": "Return only valid JSON matching the requested schema."
        },
        {
          "role": "user",
          "content": "Evaluate this CV against the HR requirements: ..."
        }
      ],
      "temperature": 0
    }
  }'
```

For token streaming, set `"stream": true` and process the returned SSE events.
For decision generation, non-streaming mode is easier to parse and validate.

The RAG team must parse the model response and validate it as `CVDecision` before
persisting the result.

## Persisting a Reviewed CV

The persistence endpoint is:

```text
POST /api/v1/cv-reviews
```

It accepts multipart form data:

```bash
curl -X POST http://localhost:8004/api/v1/cv-reviews \
  -F "cv=@candidate.pdf" \
  -F "approved=false" \
  -F "rejection_reason=Missing required experience"
```

The gateway then:

1. Uploads the original CV to MinIO.
2. Creates a review record in PostgreSQL.
3. Stores the MinIO object key with the review record.
4. Returns the saved review record.

The database record contains:

```text
id
cv_name
approved
rejection_reason
cv_object_key
created_at
```

## Future RAG Flow

The eventual orchestration should follow this order:

```text
Receive CV
  -> Extract text/OCR
  -> Retrieve HR requirements
  -> Ask the LLM for structured JSON
  -> Validate CVDecision
  -> POST the CV and decision to /api/v1/cv-reviews
```

A future RAG module can be organized like this:

```text
app/rag/
  __init__.py
  pipeline.py
  retriever.py
  prompts.py
  schemas.py
```

Suggested interface:

```python
async def analyze_cv(cv_bytes: bytes, filename: str) -> CVDecision:
    extracted_text = await extract_text(cv_bytes)
    hr_context = await retrieve_hr_context(extracted_text)
    return await evaluate_with_llm(extracted_text, hr_context)
```

The RAG team should not write directly to the database tables or construct MinIO
object keys. Use the persistence API until a shared internal service function is
agreed upon.

## Review Listing

The future frontend can read saved results with:

```bash
curl http://localhost:8004/api/v1/cv-reviews
```

Retrieve one review by ID:

```bash
curl http://localhost:8004/api/v1/cv-reviews/<review-id>
```

## Local Setup

Start PostgreSQL and MinIO:

```bash
docker compose up -d postgres llmops-s3
```

Start the gateway:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8004
```

Required environment values are documented in `.env.example`. Never commit `.env`
or API keys.

## Definition of Done for the RAG Team

- The pipeline accepts a CV file.
- OCR/text extraction works for the agreed file types.
- HR context is retrieved from the agreed knowledge source.
- The model returns a validated `CVDecision`.
- Rejected CVs always include a useful reason.
- The original CV and decision are sent to `/api/v1/cv-reviews`.
- The pipeline handles invalid model JSON and backend errors.
- A test covers both an approved and a rejected CV.
