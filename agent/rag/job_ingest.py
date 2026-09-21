"""Job ingestion: web page / .md / .txt -> structured JobRequirement + section chunks -> Qdrant.

    python -m rag.job_ingest --dir data                 # job_id = file name without extension
    python -m rag.job_ingest --url https://... --job-id backend-eng-2026

The posting is UNTRUSTED: it is parsed once into a schema here; the raw text is never injected into
agent prompts later (only the extracted fields and short evidence chunks are).
"""
import argparse
import hashlib
import re
from pathlib import Path

import dspy

from agent.dspy_setup import init_dspy, lm_ctx
from agent.logger import init_run, get_logger
from agent.signatures import ParseJob
from agent.state import JobChunk, JobExtraction, JobRequirement
from rag import store
from utils.text import detect_language

_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*)$")


def fetch_url_text(url: str) -> str:
    import trafilatura  # lazy

    html = trafilatura.fetch_url(url)
    text = trafilatura.extract(html, include_comments=False, include_tables=True) if html else None
    if not text:
        raise ValueError(f"Could not extract text from {url}")
    return text


def chunk_sections(text: str, max_chars: int = 900) -> list[JobChunk]:
    """Split on markdown headings; long sections are split on paragraphs."""
    sections: list[tuple[str, list[str]]] = [("overview", [])]
    for line in text.splitlines():
        m = _HEADING.match(line)
        if m:
            sections.append((m.group(1).strip(), []))
        else:
            sections[-1][1].append(line)
    chunks: list[JobChunk] = []
    for title, lines in sections:
        body = "\n".join(lines).strip()
        if not body:
            continue
        buf = ""
        for para in re.split(r"\n\s*\n", body):
            if buf and len(buf) + len(para) > max_chars:
                chunks.append(JobChunk(section=title, text=buf.strip()))
                buf = ""
            buf += para + "\n\n"
        if buf.strip():
            chunks.append(JobChunk(section=title, text=buf.strip()))
    return chunks


def parse_job(text: str) -> JobExtraction:
    with lm_ctx("llm"):
        return dspy.Predict(ParseJob)(job_posting=text).job


def ingest_text(job_id: str, text: str) -> JobRequirement:
    ext = parse_job(text)
    req = JobRequirement(**ext.model_dump(), job_id=job_id,
                         job_version=hashlib.sha256(text.encode()).hexdigest()[:12],
                         language=detect_language(text))
    if not req.required_skills:
        raise ValueError(f"[{job_id}] no required skills extracted; refusing to store an empty spec")
    n = store.upsert_job(req, chunk_sections(text))
    get_logger().info(f"ingested job '{job_id}' v{req.job_version} lang={req.language} "
                      f"required={len(req.required_skills)} nice={len(req.nice_to_have_skills)} points={n}")
    return req


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", help="folder of .md/.txt postings; file stem is the job_id")
    ap.add_argument("--url")
    ap.add_argument("--job-id")
    args = ap.parse_args()
    init_run("job_ingest")
    init_dspy()
    if args.url:
        if not args.job_id:
            ap.error("--url requires --job-id")
        ingest_text(args.job_id, fetch_url_text(args.url))
    for path in sorted(Path(args.dir or "").glob("*")) if args.dir else []:
        if path.suffix.lower() in {".md", ".txt"}:
            ingest_text(path.stem, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
