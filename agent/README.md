# HR AI: agentic CV evaluation (Beamdata capstone, Team 4)

```
START -> retriever -> ingest -> extractor -> validator -+-> extractor (escalate to vision)
                                                        +-> gap -> matcher -+-> recommender -> formatter
                                                        +-> formatter      +-> formatter
```
| Node | LLM? | Notes |
|---|---|---|
| retriever | no | job loaded by `job_id` payload filter; fails in ms if missing |
| ingest | no | PDF/image/DOCX/txt -> page images + Docling text layer |
| extractor | Qwen3-VL | text layer first; escalates to page images; values kept in ORIGINAL language |
| validator | no | required fields, grounding (skills/name must exist in the document), confidence |
| gap | Qwen3.5 **thinking** + ReAct | code confirms clear matches; agent loops over the whole CV (`search_cv`, `job_context`) for the rest; quote verified, one feedback round |
| matcher | Qwen3.5 (enum verdicts + justification) | score computed in code from the rubric; triage in code |
| recommender | Qwen3.5 ReAct + Tavily | catalog first; URL must come from a real search result; no PII sent |
| formatter | no | JSON + localised (EN/AR) markdown; always emits a report, even on failure |

## Install (uv)
```bash
# app env (exact, conflict-free set; resolved with `uv pip compile`)
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.lock

# vLLM lives in its OWN env (it pins its own torch)
uv venv .venv-vllm --python 3.12 && source .venv-vllm/bin/activate
uv pip install -U vllm --torch-backend=auto
```
Serve both models with `--reasoning-parser qwen3` (see your infra notes for GPU memory split).
DOCX pages need LibreOffice (`soffice`); without it DOCX uses the text layer only.

## Run
```bash
cp .env.example .env
python -m rag.job_ingest --dir data                       # ingest all synthetic and real postings
python main.py --cv cv_data/doc_0001.pdf --job-id backend_engineer
python main.py --dir cv_data --job-id qa_automation_engineer --lang ar
python -m rag.bulk --cv-dir cv_data --job-id backend_engineer --job-id devops_engineer --top-k 50
pytest -q                                                     # 24 tests, no GPU needed
```

The files in `data/` use their filename stem as the job tag. `rag.bulk` indexes
each CV once and retrieves bounded shortlists for the requested job tags; it
does not make final hiring assignments.

## Calibrate on your eval set (defaults are placeholders)
`SKILL_SIM_MET`, `SKILL_SIM_AMBIG`, `TRIAGE_*`, `CATALOG_MIN_SCORE`, `MAX_UNGROUNDED_SKILL_RATIO`.

`GAP_MODE=react|hybrid` (default react). Hybrid = single guided call on the ambiguous band only; use it for the ablation.

`DOCLING_MODE=simple|tables|full` (default simple = no OCR, so scanned CVs go to the VLM). Choose it from your
Docling benchmark (`full` vs `simple`), then compare `tables` if CVs have skill tables or multi-column layouts.

## Event-Driven Deployment (Redis Queue)
The agent now supports a highly scalable event-driven architecture using Redis. Instead of polling the backend sequentially, the agent spawns a `ThreadPoolExecutor` (10 parallel workers) and blocks securely on a Redis list (`cv_queue`), consuming 0% CPU until a CV is uploaded.

### Build the Docker Image
Make sure to build using the `agent/` folder context:
```bash
sudo docker build --no-cache -t agent ./agent
```

### Run the Agent Daemon
Use the `--network host` flag to communicate seamlessly with your local vLLM and Redis ports. Make sure your `.env` specifies `REDIS_HOST=172.17.0.1`.
```bash
sudo docker run -d --name llmops-agent \
  --restart unless-stopped \
  --network host \
  -v /home/nassir/models/hf/:/models/huggingface \
  --env-file .env \
  agent --watch
```

**Horizontal Scaling:** To process even more CVs simultaneously, simply run the above command multiple times with a new container name (e.g., `--name llmops-agent-2`). Redis acts as a perfect atomic queue and safely deals CVs out evenly across all your running agent containers!
