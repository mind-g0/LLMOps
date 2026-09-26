"""Bulk RAG workflow: extract each CV once, then retrieve shortlists per job tag.

This module deliberately stops before the expensive gap/matcher graph and before any
backend persistence. The caller can run full verification only for the returned
shortlist candidates.
"""
import argparse
from pathlib import Path
from typing import Any

from agent.dspy_setup import init_dspy
from agent.logger import get_logger, init_run
from agent.nodes.converter import converter
from agent.nodes.extractor import extractor
from agent.nodes.parser import parser
from agent.nodes.validator import validator
from agent.state import CandidateProfile, HRState
from config import settings as S
from rag import store

SUPPORTED = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".docx", ".doc", ".txt", ".md", ".json"}


def _apply(state: HRState, update: dict[str, Any]) -> HRState:
    """Apply a node's public state fields while ignoring graph-only routing metadata."""
    fields = {key: value for key, value in update.items() if not key.startswith("_")}
    return state.model_copy(update=fields)


def extract_profile(cv_path: str, output_language: str | None = None) -> CandidateProfile:
    """Ingest and validate one CV without loading or evaluating a job."""
    state = HRState(cv_path=cv_path, job_id="__bulk_index__", output_language=output_language)
    state = _apply(state, converter(state))
    if state.status == "failed":
        raise ValueError(f"conversion failed for {cv_path}")
    state = _apply(state, parser(state))
    if state.status == "failed":
        raise ValueError(f"parsing failed for {cv_path}")

    for _ in range(S.MAX_EXTRACT_ATTEMPTS):
        update = extractor(state)
        state = _apply(state, update)
        if state.profile is None:
            break
        checked = _apply(state, validator(state))
        state = checked
        if not state.retry_extract:
            break
    if state.profile is None:
        raise ValueError(f"extraction failed for {cv_path}")
    if state.validation_issues and not state.profile.flags:
        raise ValueError(f"validation failed for {cv_path}: {state.validation_issues}")
    return state.profile


def index_cv(cv_path: str, output_language: str | None = None) -> CandidateProfile:
    """Extract once and upsert the validated profile into the candidate index."""
    profile = extract_profile(cv_path, output_language)
    store.upsert_candidate(profile)
    return profile


def index_directory(folder: str, output_language: str | None = None) -> dict[str, str]:
    """Index supported files sequentially; one bad CV does not stop the batch."""
    outcomes: dict[str, str] = {}
    for path in sorted(Path(folder).iterdir()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED:
            continue
        try:
            profile = index_cv(str(path), output_language)
            outcomes[str(path)] = profile.candidate_id
        except Exception as exc:
            get_logger().warning(f"bulk index failed for {path.name}: {type(exc).__name__}: {exc}")
            outcomes[str(path)] = f"ERROR: {type(exc).__name__}: {exc}"
    return outcomes


def job_query(job_id: str) -> str:
    """Build a retrieval query from the stored structured job, not raw untrusted text."""
    found = store.get_job(job_id)
    if not found:
        raise ValueError(f"job not found: {job_id}")
    req, chunks = found
    context = "\n".join(chunk.text[:500] for chunk in chunks[:3])
    return "\n".join([
        req.title,
        "Required skills: " + ", ".join(req.required_skills),
        "Nice to have: " + ", ".join(req.nice_to_have_skills),
        "Responsibilities: " + req.responsibilities_summary,
        context,
    ])


def shortlist_job(job_id: str, top_k: int | None = None) -> list[dict]:
    """Retrieve possible candidates only; results are not hiring decisions."""
    return store.search_candidates(job_query(job_id), k=top_k or S.MATCH_TOP_K)


def main() -> None:
    parser = argparse.ArgumentParser(description="Index CVs once and retrieve bounded job shortlists")
    parser.add_argument("--cv-dir", required=True, help="directory containing CV files")
    parser.add_argument("--job-id", action="append", required=True, help="job tag; repeat for multiple jobs")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--lang", choices=["en", "ar"])
    args = parser.parse_args()

    init_run("bulk_rag")
    init_dspy()
    outcomes = index_directory(args.cv_dir, args.lang)
    print(f"indexed={sum(not value.startswith('ERROR:') for value in outcomes.values())} "
          f"failed={sum(value.startswith('ERROR:') for value in outcomes.values())}")
    for job_id in args.job_id:
        candidates = shortlist_job(job_id, args.top_k)
        print(f"{job_id}: shortlist={len(candidates)}")
        for candidate in candidates:
            profile = candidate.get("profile") or {}
            print(f"  {candidate.get('candidate_id')}: {profile.get('name', 'N/A')} "
                  f"retrieval={candidate.get('retrieval_score', 0.0):.3f}")


if __name__ == "__main__":
    main()
