# Changelog — Agent pipeline & frontend fixes

Handoff notes for the deployment team. Covers `agent/` and `frontend/` only —
`app/` (backend) was not touched in this pass. Nothing here was run against the
real deployed stack (Qdrant/vLLM/Redis are on the remote server); everything
was verified with `agent/tests/` (pytest) plus manual code tracing, so treat
this as code-reviewed, not field-tested.

## Behavior changes to be aware of

**Extraction is now vision-first for every PDF/DOCX, not just failures.**
`agent/agent/nodes/extractor.py` used to try the cheap text-only LLM path
first and only fall back to the VLM when Docling's text failed validation.
It now sends every PDF/DOCX with page images straight to the VLM (Docling's
text still rides along as a hint), falling back to text-only only when there
are literally no page images (txt/md/json, or a docx LibreOffice couldn't
render). This should reduce missed info (tables, layout-only details), but it
means **every CV now hits the OCR/VLM backend**, not just the hard cases.
Given the OCR chart caps `maxNumSeqs: 4` (`manifest/team-llmops/vllm-OCR-chart/values.yaml`)
on a GPU that's time-sliced with the text LLM, watch OCR queue depth/latency
closely after this ships — this is the most likely thing to need tuning back.

**Two ReAct iteration caps were lowered** (`agent/config/settings.py`):
- `GAP_MAX_ITERS`: 5 → 3 (skill-matching agent, `gap_analyzer` node)
- `RECOMMEND_MAX_ITERS`: 4 → 3 (learning-recommendation agent, `recommender` node)

Lower latency tail, but fewer search rounds before giving up. Worth watching:
the `missing`-skill rate out of `gap_analyzer` and the `unresolved_skills`
rate out of `recommender`, in case either climbs noticeably.

## Fixes

- **CV review results were showing wrong/misleading data in the frontend.**
  `rejection_reason` was a raw internal code (e.g. `stated_vs_computed_years`)
  instead of readable text; "Match Breakdown" was labeled as `%` when the
  values are actually points out of different per-category maximums
  (Experience/35, Skills/30, Education/20, Projects+Certs/15); "Strengths"
  and "Matching Requirements" always showed identical content. All three
  fixed — see `agent/agent/nodes/formatter.py` (`humanize_code`),
  `agent/main.py`, `frontend/src/components/CvDetail.tsx`.
- **A job with no required skills configured produced a confusing, empty-
  looking report** with no explanation. `matcher.py` now adds a
  `job_has_no_required_skills` flag that surfaces as a readable review
  reason instead of silently empty sections.
- **Non-CV uploads (e.g. an invoice) could still get a numeric match score.**
  `validator.py` now hard-stops before scoring when the extraction found
  *nothing* usable at all (no name AND no skills AND no experience/education
  simultaneously) — narrow on purpose, so a genuinely weak-but-real CV is
  never blocked, only documents that aren't CVs at all.
- **`ingest.py` did two unrelated jobs in one node** (file→image conversion,
  and text parsing). Split into `agent/agent/nodes/converter.py` and
  `agent/agent/nodes/parser.py`; graph node `gap` renamed to `gap_analyzer`
  for clarity. Purely structural — no behavior change from the split itself.
  `agent/rag/bulk.py` (a separate CLI script) imported the old `ingest`
  module directly and would have broken on this split; fixed alongside it.
- **"RAG Summary" label renamed to "Summary"** in the frontend
  (`frontend/src/locales/en.json`, `ar.json`) — internal field name
  (`ragSummary`) unchanged, display text only.
- **`agent/tests/test_pipeline.py` was silently broken before any of this**
  (`from main import run_one` — that function didn't exist in `agent/main.py`,
  apparently dropped in an earlier refactor to the backend-polling
  architecture). The whole file failed to even collect, so none of its tests
  were running. Restored `run_one` as a thin, additive helper in
  `agent/main.py` (used by tests/CLI debugging only; the production
  backend-polling flow still uses `process_one`, unchanged).

## Files changed

```
agent/agent/nodes/converter.py   new (split from ingest.py)
agent/agent/nodes/parser.py      new (split from ingest.py)
agent/agent/nodes/ingest.py      deleted
agent/agent/state.py             + raw_text_layer field
agent/agent/graph.py             converter/parser wiring, gap -> gap_analyzer
agent/agent/nodes/extractor.py   vision-first extraction
agent/agent/nodes/validator.py   not-a-CV hard-stop gate
agent/agent/nodes/matcher.py     job_has_no_required_skills flag
agent/agent/nodes/formatter.py   humanize_code() + new label codes
agent/main.py                    translated rejection_reason, run_one restored
agent/rag/bulk.py                fixed import broken by the ingest.py split
agent/config/settings.py         GAP_MAX_ITERS, RECOMMEND_MAX_ITERS lowered
agent/tests/test_pipeline.py     updated for converter/parser, run_one restored
agent/tests/test_deterministic.py  new tests (not-a-CV gate, skills flag, humanize_code)

frontend/src/components/CvDetail.tsx   breakdown as points/max, removed duplicate section
frontend/src/api.ts                    removed dead matchingRequirements field
frontend/src/locales/en.json           RAG Summary -> Summary, removed dead keys
frontend/src/locales/ar.json           same, Arabic
```

