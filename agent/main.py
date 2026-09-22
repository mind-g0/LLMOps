"""
HR CV review agent — watches the backend for new CVs and processes them.

Flow:
1. Poll GET /api/v1/cv-reviews?status=needs_human_review
2. For each unprocessed review (rag_summary is null):
   a. Fetch CV via GET /api/v1/cv-reviews/{id}/file-content
   b. Look up job from Qdrant using job_requirement_id
   c. Run the LangGraph analysis pipeline
   d. PATCH results back to the backend immediately
3. Sleep and repeat

Usage:
    python main.py --once        # process all pending CVs and exit
    python main.py --watch       # run as a daemon, poll every N seconds
    python main.py --interval 10 # override poll interval (default 30s)
"""
import argparse
import json
import time
import uuid
from pathlib import Path
from urllib import request as http
from urllib.error import URLError

from agent.dspy_setup import init_dspy
from agent.graph import build_graph
from agent.logger import get_logger, init_run
from agent.nodes.formatter import render_markdown
from agent.state import HRReport, HRState, JobChunk, JobRequirement, RDEMError
from config import settings as S
from rag import store


def _api_get(path: str) -> dict | list:
    """GET request to the backend API. Returns parsed JSON."""
    url = f"{S.BACKEND_API_BASE.rstrip('/')}{path}"
    with http.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _api_patch(path: str, body: dict) -> None:
    """PATCH request to the backend API."""
    url = f"{S.BACKEND_API_BASE.rstrip('/')}{path}"
    data = json.dumps(body).encode()
    req = http.Request(url, data=data, method="PATCH",
                       headers={"Content-Type": "application/json"})
    with http.urlopen(req, timeout=30):
        pass


def fetch_cv_bytes(cv_id: str) -> tuple[bytes, str]:
    """Download CV from backend, return (bytes, filename)."""
    url = f"{S.BACKEND_API_BASE.rstrip('/')}/api/v1/cv-reviews/{cv_id}/file-content"
    with http.urlopen(url, timeout=60) as resp:
        return resp.read(), f"cv-{cv_id}"


def process_one(graph, review: dict) -> None:
    """Analyse a single CV and save results to the backend."""
    cv_id = review["id"]
    job_id = review.get("job_requirement_id")
    cv_name = review.get("cv_name", f"cv-{cv_id}")

    log = get_logger()
    log.info(f"Processing {cv_name} ({cv_id}) ...")

    # 1. Fetch CV bytes
    try:
        data, stem = fetch_cv_bytes(cv_id)
    except Exception as e:
        log.error(f"  [{cv_id}] fetch CV failed: {e}")
        return

    # 2. Write to temp file preserving original extension
    cv_path = S.TMP_DIR / cv_id / cv_name
    cv_path.parent.mkdir(parents=True, exist_ok=True)
    cv_path.write_bytes(data)

    # 3. Validate job exists in Qdrant
    if not job_id:
        log.warning(f"  [{cv_id}] no job_requirement_id — skipping")
        return
    job = store.get_job(job_id)
    if not job or not job[0].required_skills:
        log.warning(f"  [{cv_id}] job '{job_id}' not found in Qdrant — sync it first")
        return

    # 4. Run pipeline
    state = HRState(cv_path=str(cv_path), job_id=job_id, output_language=None)
    try:
        out = graph.invoke(state, config={"configurable": {"thread_id": str(uuid.uuid4())}})
        report: HRReport = out["report"] if isinstance(out, dict) else out.report
    except Exception as e:
        log.error(f"  [{cv_id}] pipeline crashed: {e}")
        return

    # 5. Map results to backend status
    m = report.match
    if not m:
        status = "needs_human_review"
        rag_summary = ""
        rejection_reason = None
        match_score = None
    else:
        bucket_map = {"auto_accept": "approved", "auto_reject": "not_approved", "review": "needs_human_review"}
        status = bucket_map.get(m.triage_bucket, "needs_human_review")
        rag_summary = m.justification
        rejection_reason = m.review_reasons[0] if m.review_reasons else None
        match_score = m.match_score

    strengths = []
    missing = []
    if report.skill_gap:
        for v in report.skill_gap.verdicts:
            if v.verdict == "met":
                strengths.append(v.skill)
        missing = report.skill_gap.missing_skills

    # 6. PATCH results back to backend
    body = {"status": status, "rag_summary": rag_summary or "",
            "strengths": strengths, "missing_requirements": missing,
            "report_data": report.model_dump(mode="json")}
    if match_score is not None:
        body["match_score"] = match_score
    if rejection_reason:
        body["rejection_reason"] = rejection_reason

    try:
        _api_patch(f"/api/v1/cv-reviews/{cv_id}", body)
        log.info(f"  [{cv_id}] saved: status={status} score={match_score}")
    except Exception as e:
        log.error(f"  [{cv_id}] save failed: {e}")

    # 7. Save locally too (for debugging)
    S.RESULT_DIR.mkdir(exist_ok=True)
    stem = f"{cv_id}__{job_id}"
    (S.RESULT_DIR / f"{stem}.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (S.RESULT_DIR / f"{stem}.md").write_text(render_markdown(report), encoding="utf-8")


def pending_reviews() -> list[dict]:
    """Fetch reviews that need processing (status=needs_human_review, ordered oldest first)."""
    try:
        result = _api_get("/api/v1/cv-reviews?status=needs_human_review&page_size=50&sort=oldest")
    except Exception as e:
        get_logger().warning(f"poll failed: {e}")
        return []

    items = result.get("items", []) if isinstance(result, dict) else result
    return [
        r for r in items
        if not r.get("rag_summary") and r.get("job_requirement_id")
    ]


def sync_all_jobs() -> None:
    """Auto-sync all active backend jobs into Qdrant — no manual sync needed."""
    log = get_logger()
    try:
        jobs = _api_get("/api/v1/job-requirements")
    except Exception as e:
        log.warning(f"sync_all_jobs: cannot fetch jobs from backend: {e}")
        return

    if not jobs:
        log.info("No active jobs to sync.")
        return

    count = 0
    for job in jobs:
        job_id = str(job.get("id", ""))
        if not job_id:
            continue
        try:
            spec = _api_get(f"/api/v1/job-requirements/{job_id}/spec")
        except Exception as e:
            log.warning(f"sync_all_jobs: cannot fetch spec for {job_id}: {e}")
            continue
        req = JobRequirement(
            job_id=spec["job_id"],
            job_version="backend",
            title=spec.get("title", ""),
            required_skills=spec.get("required_skills", []),
            nice_to_have_skills=[],
            min_experience_years=0.0,
            education_requirement="",
            language_requirements=[],
            responsibilities_summary=spec.get("description", "")[:500],
            language="en",
        )
        desc = spec.get("description", "")
        chunks = [JobChunk(section="description", text=desc[:900])] if desc else []
        store.upsert_job(req, chunks)
        count += 1
    log.info(f"Synced {count} job(s) into Qdrant.")


def main() -> None:
    ap = argparse.ArgumentParser(description="HR CV review agent — processes pending CVs from the backend")
    ap.add_argument("--once", action="store_true", help="process all pending CVs and exit")
    ap.add_argument("--watch", action="store_true", help="run as a daemon, polling for new CVs")
    ap.add_argument("--interval", type=int, default=30, help="seconds between polls in --watch mode")
    a = ap.parse_args()

    if not (a.once or a.watch):
        ap.error("provide --once or --watch")
    if not S.BACKEND_API_BASE:
        ap.error("BACKEND_API_BASE is required")

    init_run("agent_watch")
    init_dspy()
    graph = build_graph()
    log = get_logger()

    log.info(f"Agent started (BACKEND_API_BASE={S.BACKEND_API_BASE})")
    log.info(f"Mode: {'watch' if a.watch else 'once'}")

    sync_all_jobs()

    while True:
        reviews = pending_reviews()
        if not reviews:
            log.info("No pending CVs found.")
        else:
            log.info(f"Found {len(reviews)} pending CV(s).")
            for review in reviews:
                process_one(graph, review)

        if not a.watch:
            break
        time.sleep(a.interval)


if __name__ == "__main__":
    main()