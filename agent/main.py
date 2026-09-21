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
from agent.state import HRReport, HRState, RDEMError
from config import settings as S

SUPPORTED = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".docx", ".doc", ".txt", ".md", ".json"}


def default_job_id(jobs_dir: str = "data") -> str | None:
    """job_ingest uses the file stem as job_id, so with exactly one posting we can infer it."""
    files = [p for p in Path(jobs_dir).glob("*") if p.suffix.lower() in {".md", ".txt"}]
    return files[0].stem if len(files) == 1 else None


def fetch_cv_from_backend(cv_id: str) -> Path:
    """Download a CV from the backend API and write to a temp file."""
    base = S.BACKEND_API_BASE.rstrip("/")
    url = f"{base}/api/v1/cv-reviews/{cv_id}/file-content"
    with http.urlopen(url, timeout=60) as resp:
        data = resp.read()
    name = f"backend-cv-{cv_id}.pdf"
    dest = (S.TMP_DIR / name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


def _triage_status(report: HRReport) -> str:
    """Map agent triage bucket to backend review status."""
    m = report.match
    if not m:
        return "needs_human_review"
    return {"auto_accept": "approved", "auto_reject": "not_approved", "review": "needs_human_review"}.get(
        m.triage_bucket, "needs_human_review"
    )


def save_to_backend(report: HRReport, cv_id: str, job_id: str) -> None:
    """PATCH the backend CV review with the agent's analysis results."""
    base = S.BACKEND_API_BASE.rstrip("/")
    url = f"{base}/api/v1/cv-reviews/{cv_id}"

    strengths = []
    missing = []
    if report.skill_gap:
        for v in report.skill_gap.verdicts:
            if v.verdict == "met":
                strengths.append(v.skill)
        missing = report.skill_gap.missing_skills

    body = {
        "status": _triage_status(report),
        "rag_summary": report.match.justification if report.match else "",
        "strengths": strengths,
        "missing_requirements": missing,
        "match_score": report.match.match_score if report.match else None,
        "rejection_reason": report.match.review_reasons[0] if (report.match and report.match.review_reasons) else None,
    }
    body = {k: v for k, v in body.items() if v is not None}
    data = json.dumps(body).encode()

    req = http.Request(url, data=data, method="PATCH",
                       headers={"Content-Type": "application/json"})
    try:
        with http.urlopen(req, timeout=30) as resp:
            if resp.status >= 400:
                get_logger().warning(f"save_to_backend returned {resp.status}: {resp.read().decode()[:200]}")
            else:
                get_logger().info(f"Saved analysis to backend review {cv_id}")
    except URLError as e:
        get_logger().warning(f"save_to_backend failed: {e}")


def run_one(graph, cv_path: str, job_id: str, lang: str | None = None) -> HRReport:
    state = HRState(cv_path=cv_path, job_id=job_id, output_language=lang)
    try:
        out = graph.invoke(state, config={"configurable": {"thread_id": str(uuid.uuid4())}})
        report = out["report"] if isinstance(out, dict) else out.report
    except Exception as e:  # last resort: still return a structured failure
        get_logger().exception("pipeline crashed")
        report = HRReport(status="failed", job_id=job_id, errors=[
            RDEMError(node="graph", error_type=type(e).__name__, message=str(e)[:300])])
    return report


def result_stem(cv_path: str, job_id: str) -> str:
    return f"{Path(cv_path).stem}__{job_id}"


def save_local(report: HRReport, cv_path: str) -> Path:
    S.RESULT_DIR.mkdir(exist_ok=True)
    stem = result_stem(cv_path, report.job_id)
    (S.RESULT_DIR / f"{stem}.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    md = S.RESULT_DIR / f"{stem}.md"
    md.write_text(render_markdown(report), encoding="utf-8")
    return md


def is_done(cv_path: Path, job_id: str) -> bool:
    return (S.RESULT_DIR / f"{result_stem(str(cv_path), job_id)}.json").exists()


def is_stable(path: Path, wait: float = 1.0) -> bool:
    """True if the file size is unchanged over `wait` seconds (i.e. not still being copied)."""
    try:
        size = path.stat().st_size
        time.sleep(wait)
        return size == path.stat().st_size and size > 0
    except OSError:
        return False


def list_new(folder: Path, job_id: str, seen: set[str], skip_done: bool) -> list[Path]:
    """CVs not yet attempted in this run. With skip_done, also drop CVs that already have a result."""
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED)
    return [p for p in files
            if str(p) not in seen and not (skip_done and is_done(p, job_id))]


def process(graph, f: Path, job_id: str, lang: str | None, save: bool, cv_id: str | None) -> None:
    report = run_one(graph, str(f), job_id, lang)
    md = save_local(report, str(f))
    if save:
        rid = cv_id or f.stem  # --cv-id uses the real ID; --cv uses the file stem as placeholder
        save_to_backend(report, rid, job_id)
    m = report.match
    print(f"{f.name}: {report.status}"
          + (f" score={m.match_score} bucket={m.triage_bucket}" if m else "") + f" -> {md}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cv", help="a single CV file")
    ap.add_argument("--dir", help="folder of CVs; every supported file is processed")
    ap.add_argument("--cv-id", help="CV review ID to fetch from the backend API")
    ap.add_argument("--job-id", help="job to match against (default: the only posting in data/)")
    ap.add_argument("--lang", choices=["en", "ar"], help="force output language (default: match the CV)")
    ap.add_argument("--watch", action="store_true", help="after the first pass, keep running and process new files")
    ap.add_argument("--interval", type=float, default=5.0, help="seconds between folder scans in --watch mode")
    ap.add_argument("--skip-done", action="store_true",
                    help="skip CVs that already have a result (default: run all CVs)")
    ap.add_argument("--save", action="store_true",
                    help="save analysis results back to the backend API (requires BACKEND_API_BASE)")
    a = ap.parse_args()

    if not (a.cv or a.dir or a.cv_id):
        ap.error("provide --cv, --dir, or --cv-id")
    if a.watch and not a.dir:
        ap.error("--watch requires --dir")
    if a.save and not S.BACKEND_API_BASE:
        ap.error("--save requires BACKEND_API_BASE in the environment")
    a.job_id = a.job_id or default_job_id()
    if not a.job_id:
        ap.error("--job-id is required (data/ has zero or several postings)")

    init_run()
    init_dspy()
    graph = build_graph()

    if a.cv:
        process(graph, Path(a.cv), a.job_id, a.lang, a.save, None)
        return

    if a.cv_id:
        cv_path = fetch_cv_from_backend(a.cv_id)
        process(graph, cv_path, a.job_id, a.lang, a.save, a.cv_id)
        return

    folder = Path(a.dir)
    if not folder.is_dir():
        ap.error(f"--dir '{folder}' is not a folder")

    seen: set[str] = set()
    try:
        while True:
            new = list_new(folder, a.job_id, seen, a.skip_done)
            for f in new:
                if a.watch and not is_stable(f):
                    continue
                seen.add(str(f))
                process(graph, f, a.job_id, a.lang, a.save, None)
            if not a.watch:
                if not new:
                    print(f"No CVs to process in {folder} for job '{a.job_id}'.")
                break
            time.sleep(a.interval)
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()