"""Ingest a backend job requirement into the agent's Qdrant vector store.

Usage:
    python -m agent.rag.sync_job <job-uuid>            # single job
    python -m agent.rag.sync_job --all                  # all active jobs from backend

Requires BACKEND_API_BASE in the environment.
"""
import argparse
import json
import sys
from urllib import request as http
from urllib.error import URLError

from agent.logger import get_logger
from agent.state import JobChunk, JobRequirement
from rag import store


def fetch_spec(job_id: str, backend_url: str) -> dict:
    url = f"{backend_url.rstrip('/')}/api/v1/job-requirements/{job_id}/spec"
    with http.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read().decode())


def fetch_all(backend_url: str) -> list[dict]:
    url = f"{backend_url.rstrip('/')}/api/v1/job-requirements"
    with http.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode())


def to_agent_job(spec: dict) -> JobRequirement:
    return JobRequirement(
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


def ingest(spec: dict) -> None:
    req = to_agent_job(spec)
    desc = spec.get("description", "")
    chunks = [JobChunk(section="description", text=desc[:900])] if desc else []
    n = store.upsert_job(req, chunks)
    get_logger().info(f"[sync] ingested job '{req.job_id}' "
                      f"required={len(req.required_skills)} points={n}")


def main() -> None:
    # load env for Qdrant connection
    from dotenv import load_dotenv
    import os
    load_dotenv()

    backend_url = os.getenv("BACKEND_API_BASE", "http://localhost:8004")

    ap = argparse.ArgumentParser(description="Sync backend jobs into the agent's Qdrant store")
    ap.add_argument("job_id", nargs="?", help="single job UUID to sync")
    ap.add_argument("--all", action="store_true", help="sync all active jobs")
    args = ap.parse_args()

    if args.all:
        specs = fetch_all(backend_url)
        for s in specs:
            try:
                ingest(s)
            except Exception as e:
                print(f"ERROR syncing job {s.get('id', '?')}: {e}", file=sys.stderr)
        print(f"Synced {len(specs)} jobs.")
    elif args.job_id:
        spec = fetch_spec(args.job_id, backend_url)
        ingest(spec)
        print(f"Synced job {args.job_id}.")
    else:
        ap.error("provide a job_id or --all")


if __name__ == "__main__":
    main()