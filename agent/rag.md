# HR CV Evaluation: Full RAG and Backend Integration Plan

This document is the integration contract for the complete HR CV evaluation system. It describes the implemented workflow, model and retrieval boundaries, report contract, and backend work required to accept CVs and persist reviewed results.

The system receives CVs and job tags, produces validated and explainable evaluations, and submits approved decisions to the backend persistence API. The RAG pipeline must not connect directly to PostgreSQL or MinIO.

## 1. End-to-End Workflow

```text
CV batch + active job tags
  -> ingest and extract each CV once
  -> index validated candidate profile and evidence
  -> retrieve a bounded shortlist for each job using vectors and hard filters
  -> verify only shortlisted candidate/job pairs
  -> rank and assign only high-confidence, unambiguous matches
  -> send ambiguous pairs to human review
  -> persist the original CV and validated decision
```

The implemented LangGraph routing is:

```text
START -> retriever -> ingest -> extractor -> validator -+-> extractor
                                                        +-> gap -> matcher -+-> recommender -> formatter
                                                        |                   +-> formatter
                                                        +-> formatter (failed)
```

`retriever`, `ingest`, `validator`, `gap`, `matcher`, `recommender`, and `formatter` are the graph nodes. Transient gateway failures are retried for the retriever and recommender; deterministic failures are carried as structured errors and routed to the formatter.

## 2. Runtime Entry Points

`main.py` accepts one CV or a directory:

```bash
python main.py --cv cv_data/ahmed.pdf --job-id backend_engineer
python main.py --dir cv_data --job-id backend_engineer --lang ar
python main.py --dir cv_data --job-id backend_engineer --watch
```

For each file, `main.run_one()` creates `HRState`, invokes the compiled graph, and receives an `HRReport`. The current CLI saves:

```text
result/<cv-stem>__<job-id>.json
result/<cv-stem>__<job-id>.md
```

The production backend integration must call the same graph from an API or worker adapter and submit the original bytes. It must not reconstruct a decision by parsing Markdown.

## 2A. Scalable Bulk Matching

Do not fully score every candidate against every job. With 300 CVs and 20 jobs,
that creates 6,000 candidate/job evaluations. Running the gap agent and matcher
for all 6,000 pairs is expensive, slow, and increases the number of model
outputs that must be audited.

Use a two-stage retrieval architecture instead:

```text
300 CVs
  -> extract each CV once
  -> validate and store CandidateProfile + evidence chunks
  -> create one or more candidate vectors

20 job tags
  -> ingest each JobRequirement once
  -> create job vectors and structured hard filters

each job
  -> Qdrant top-K candidate retrieval
  -> hard-filter by location, language, work authorization, seniority, or required years
  -> cheap exact/embedding skill gate
  -> full gap verification only for the remaining shortlist
  -> assign, reject, or hold for review
```

The cost becomes approximately `O(C + J + J*K)` instead of `O(C*J)`, where `C`
is the number of CVs, `J` is the number of jobs, and `K` is a small shortlist
such as 10 to 30. The exact `K` must be measured on a labeled recall set. A
shortlist is allowed to be larger when the job is broad or the retrieval
confidence is low.

Candidate indexing should store:

```text
candidate_id, source_file_hash, profile_version, language
normalized_titles, seniority, experience_years, locations
skills, education, eligibility metadata
evidence_chunk_ids, parse_confidence, validation_flags
```

Keep the original CV and extracted evidence separate. The vector payload must
never be treated as proof by itself: final positive decisions still require
verbatim evidence from the source CV or a linked extracted span.

Use separate vectors for the candidate summary, skills, and experience/project
evidence where useful. A job query should combine its title, required skills,
responsibilities, and seniority. Do not embed only the job title because that
will retrieve candidates with similar titles but the wrong capabilities.

### Assignment policy

Retrieval produces candidates for a job; it does not automatically assign them.
After shortlist verification, assign a candidate to a job only when all of these
are true:

- the job tag exists and the job version is current;
- required-skill coverage passes the configured minimum;
- evidence is verified for every skill used as a positive decision reason;
- parse and match confidence meet the configured thresholds;
- no unresolved validation or data-quality flag forces review; and
- the candidate is not ambiguous between jobs, unless the business explicitly
  allows multiple assignments.

If a CV is eligible for several jobs, keep the per-job results but assign the
candidate using a deterministic policy such as job priority, recruiter demand,
or a minimum score margin over the next eligible job. If there is no approved
policy or the margin is too small, use `needs_review`. Never choose a job merely
because it was processed first.

The system should persist a lightweight `candidate_job_match` record for every
shortlisted pair, not a full LLM report for every possible pair:

```text
candidate_id, job_id, job_version, retrieval_score
skill_gate_result, verified_skill_coverage
match_score, match_confidence, triage_bucket
review_reasons, evidence_refs, assignment_status
```

Full reports and backend review records are created only for assigned or
human-reviewed candidates. This keeps the bulk workflow auditable without
creating thousands of redundant model reports.

### Required backend adapter

Add an application/service boundary equivalent to:

```python
async def review_cv(cv_bytes: bytes, filename: str, job_id: str) -> CVReviewResult:
    """Run the graph, validate the decision, and persist through the gateway."""
```

The adapter must:

1. Store the upload temporarily, or pass it through an agreed file abstraction for the existing `HRState.cv_path` interface.
2. Run the graph with the requested `job_id` and output language.
3. Reject failed or incomplete reports before persistence.
4. Convert the report to the backend decision schema using typed validation.
5. POST the original bytes and validated decision to the gateway.
6. Return the gateway review record, including its review ID and object key.

The adapter owns HTTP timeouts, request IDs, authentication, temporary-file cleanup, and backend error handling. It must not write PostgreSQL rows or construct MinIO object keys.

## 3. Job and RAG Ingestion

Job postings are ingested before CV evaluation:

```bash
python -m rag.job_ingest --dir data
python -m rag.job_ingest --url https://example.com/job --job-id backend_engineer
```

`rag.job_ingest` reads Markdown, text, or a web page; extracts `JobExtraction` with a guided LLM call; assigns `job_id`, a content-hash `job_version`, and detected language; splits the posting into section chunks; refuses to store a job with no required skills; and stores the structured requirement and chunks in Qdrant.

`rag.store` stores one `spec` point and one or more `chunk` points in the `hr_jobs` collection. Retrieval is an exact `job_id` payload lookup, not similarity search. A missing job fails before CV extraction. Qdrant also supports optional `course_catalog` and `web_search_cache` collections. Embeddings use multilingual `BAAI/bge-m3` by default.

## 4. CV Ingestion and Extraction

Supported input types are PDF, PNG, JPG/JPEG, WebP, DOC/DOCX, TXT, Markdown, and JSON.

`agent.nodes.ingest` validates the file, creates a stable candidate ID from its bytes, extracts text, renders PDF pages, renders DOC/DOCX through LibreOffice when available, resizes page images, limits page count, and evaluates text usability using length, alphanumeric, and Arabic presentation-form checks.

If the text layer is usable, `extractor` makes a guided structured text extraction call. If it is missing or invalid and page images exist, it escalates to the vision model. The vision model sees images as authoritative and text only as a hint. Without LibreOffice, DOCX still works through its text path but visual escalation is unavailable.

The model emits `CandidateExtraction`, not the final system profile. Code adds the candidate ID, source filename, language fields, parse method, and computed experience years. LLM-provided total experience is never the authoritative score input.

## 5. Validation and Grounding

`validator` is deterministic. It checks required fields, grounds extracted skills and name against usable source text, checks the ungrounded skill ratio, detects date and employment anomalies, computes completeness and parse confidence, and resolves the English or Arabic output language.

When validation fails and page images are available, the graph retries with vision according to `MAX_EXTRACT_ATTEMPTS`. After retries are exhausted, the profile is retained with an `unresolved_validation` flag and eventual triage is forced to human review. Missing profiles and unrecoverable ingestion failures produce a failed report with `RDEMError` entries.

## 6. Skill Gap Analysis

`gap_agent` evaluates required and nice-to-have skills in posting order:

1. Normalized exact and embedding matches are confirmed in code.
2. Ambiguous or low-similarity skills are investigated with `GAP_MODE=react` (bounded thinking agent using `search_cv` and `job_context`) or `GAP_MODE=hybrid` (one guided judge call).
3. A verdict is `met`, `partial`, or `missing`.
4. Positive verdicts require a verbatim quote from retrieved CV evidence.
5. An unverifiable quote triggers one feedback/search attempt; if it remains unverifiable, the verdict is downgraded.

The output is `SkillGap`, containing every `SkillVerdict`, missing and partial skill lists, and embedding-only coverage. Evidence includes skills, experience, projects, certifications, and summary, not just the skills list.

## 7. Scoring, Confidence, and Triage

`matcher` asks the model only for qualitative enums: experience relevance, education fit, and project/certification strength. The numeric score is calculated in code:

| Component | Weight |
|---|---:|
| Experience | 35 |
| Skills | 30 |
| Education | 20 |
| Projects and certifications | 15 |

Skill credit is `met=1.0`, `partial=0.5`, and `missing=0.0`. Nice-to-have skills use the configured reduced weight. Confidence combines parse quality, agreement between embedding and final skill coverage, profile completeness, and anomaly flags.

Triage is deterministic:

- `auto_accept` when score is at least `TRIAGE_ACCEPT_SCORE`, confidence is sufficient, and there are no review flags;
- `auto_reject` when score is at most `TRIAGE_REJECT_SCORE`, confidence is sufficient, and there are no review flags; and
- `review` for low confidence, anomalies, unresolved validation, failed qualitative assessment, or a middle-band score.

Thresholds are configuration placeholders and must be calibrated on a labeled evaluation set before automatic hiring decisions are enabled. The model-written justification is localized to English or Arabic, checked for the requested language, and retried once when needed. `MatchResult` contains the score, breakdown, triage bucket, review reasons, and justification.

## 8. Recommendations

When enabled and gaps exist, `recommender` selects configured missing or partial skills. It searches the Qdrant course catalog first and then uses the Tavily-backed ReAct search when no catalog result meets the threshold.

No candidate PII is sent to web search. A returned URL must occur in an actual search result. Reasons are generated in the target language. Failed resources are reported in `unresolved_skills`, never fabricated. Recommendations are enrichment, not a requirement for a valid evaluation.

## 9. Typed Report Contract

The graph always ends at `formatter`, which produces `HRReport` even when a node fails. The report includes:

```text
status, candidate_id, job_id, job_version
detected_language, target_language, parse_method
profile, skill_gap, match
recommendations, unresolved_skills, flags, errors, timings_s
```

The JSON report is the machine contract. Markdown is a human-readable view and must never be used as another service's input.

For a successful report, `profile`, `skill_gap`, and `match` must be present. A failed report must not be persisted as an approved or rejected hiring decision; return it as an integration error or store it in a separate failed-processing record if supported.

## 10. Backend Decision Contract

The gateway persistence API is the only database and object-storage boundary:

```text
POST /api/v1/cv-reviews
```

The request is multipart form data containing the original file and a validated decision:

```text
cv=<original uploaded bytes>
approved=<boolean>
rejection_reason=<string or null>
```

Recommended adapter schema:

```python
from pydantic import BaseModel, model_validator


class CVDecision(BaseModel):
    approved: bool
    rejection_reason: str | None = None

    @model_validator(mode="after")
    def rejected_candidates_need_a_reason(self):
        if not self.approved and not self.rejection_reason:
            raise ValueError("rejected candidates require rejection_reason")
        return self
```

The current repository does not yet implement this adapter or endpoint call. The mapping must be agreed with HR:

- `auto_accept` -> `approved=True`;
- `auto_reject` -> `approved=False`, with a reason derived from missing skills, score, and localized justification; and
- `review` -> do not silently convert to approval or rejection. Use a backend-supported `needs_review` status or hold it for a human under an explicitly agreed contract.

If the backend accepts only `approved: bool`, it must define the policy for `review`. A guessed boolean would destroy the meaning of confidence and review safeguards.

The gateway is responsible for uploading the original CV to MinIO, creating the PostgreSQL review row, generating the object key, and returning the saved review record. RAG code must not duplicate those integrations.

## 11. Gateway Model Contract

All model requests go through the configured gateway. The application uses:

```text
POST <LLM_API_BASE>/chat/completions
```

with this wrapped shape:

```json
{
  "task_type": "llm",
  "payload": {
    "stream": false,
    "messages": [],
    "temperature": 0,
    "response_format": {
      "type": "json_schema",
      "json_schema": {}
    }
  }
}
```

`agent.dspy_setup.GatewayLM` converts Pydantic outputs to JSON Schema, supports optional SSE stitching, retries transport/5xx/429 failures, and converts responses back to the DSPy/LiteLLM shape. Callers do not choose a backend model; the gateway routes by `task_type`.

| Kind | Gateway task | Use |
|---|---|---|
| `llm` | `llm` | extraction, skill judging, matching, explanations |
| `reasoner` | `llm` | bounded ReAct agents with thinking enabled |
| `ocr` | `ocr` | page-image CV extraction |

Prompts treat CVs, job postings, and web results as untrusted data. Instructions inside those documents must never be followed.

## 12. Persistence and API Integration Checklist

The full backend integration is complete only when these items are implemented:

- [ ] upload endpoint accepts agreed CV types and returns a request/review ID;
- [ ] worker or service invokes the existing graph with a stable job ID;
- [ ] job ingestion runs before evaluation and job versions are recorded;
- [ ] successful reports are validated before persistence;
- [ ] `auto_accept` and `auto_reject` mapping is approved by HR;
- [ ] `review` has an explicit backend representation and human workflow;
- [ ] rejected decisions always contain a useful reason;
- [ ] original CV bytes and typed decision are sent to the gateway;
- [ ] backend errors, gateway timeouts, invalid model output, missing jobs, and failed extraction are observable and retryable where appropriate;
- [ ] gateway storage failure/retry semantics are agreed; and
- [ ] frontend listing and single-review APIs expose status, decision, reason, score, confidence, flags, and processing errors as agreed.

## 13. Local Setup and Verification

```bash
python -m rag.job_ingest --dir data
python main.py --dir cv_data --job-id backend_engineer
python -m rag.bulk --cv-dir cv_data --job-id backend_engineer --job-id devops --top-k 50
pytest -q
```

`rag.bulk` is the RAG-side bulk path. It extracts and validates each CV once,
upserts the profile into `hr_candidates`, and retrieves a bounded shortlist for
each repeated `--job-id`. The shortlist is only a retrieval result; the normal
job-specific graph must still verify shortlisted evidence before any assignment.
It does not call PostgreSQL, MinIO, or the DevOps team's integration APIs.

Set `QDRANT_URL` for a remote Qdrant instance; an empty value uses embedded local Qdrant. Install LibreOffice when visual DOCX fallback is required. Keep `LOG_PROMPTS=false` for personal-data protection unless prompt logging is explicitly approved.

Existing tests cover deterministic scoring and validation, missing-job short-circuiting, text-to-vision escalation, English and Arabic reports, recommendation safeguards, and the graph with model boundaries stubbed. Add backend adapter tests for approved, rejected, held-for-review, invalid decision data, and persistence failure before enabling upload automation.
