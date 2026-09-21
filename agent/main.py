import argparse
import time
import uuid
from pathlib import Path
 
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
 
 
def save(report: HRReport, cv_path: str) -> Path:
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
 
 
def process(graph, f: Path, job_id: str, lang: str | None) -> None:
    report = run_one(graph, str(f), job_id, lang)
    md = save(report, str(f))
    m = report.match
    print(f"{f.name}: {report.status}"
          + (f" score={m.match_score} bucket={m.triage_bucket}" if m else "") + f" -> {md}")
 
 
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cv", help="a single CV file")
    ap.add_argument("--dir", help="folder of CVs; every supported file is processed")
    ap.add_argument("--job-id", help="job to match against (default: the only posting in data/)")
    ap.add_argument("--lang", choices=["en", "ar"], help="force output language (default: match the CV)")
    ap.add_argument("--watch", action="store_true", help="after the first pass, keep running and process new files")
    ap.add_argument("--interval", type=float, default=5.0, help="seconds between folder scans in --watch mode")
    ap.add_argument("--skip-done", action="store_true",
                    help="skip CVs that already have a result (default: run all CVs)")
    a = ap.parse_args()
 
    if not (a.cv or a.dir):
        ap.error("provide --cv or --dir")
    if a.watch and not a.dir:
        ap.error("--watch requires --dir")
    a.job_id = a.job_id or default_job_id()
    if not a.job_id:
        ap.error("--job-id is required (data/ has zero or several postings)")
 
    init_run()
    init_dspy()
    graph = build_graph()
 
    if a.cv:
        process(graph, Path(a.cv), a.job_id, a.lang)
        return
 
    folder = Path(a.dir)
    if not folder.is_dir():
        ap.error(f"--dir '{folder}' is not a folder")
 
    seen: set[str] = set()  # attempted in this run, so a failing file is never retried in a loop
    try:
        while True:
            new = list_new(folder, a.job_id, seen, a.skip_done)
            for f in new:  # sequential: one GPU; batch concurrency is a benchmark knob, not a default
                if a.watch and not is_stable(f):
                    continue  # still being copied; picked up on the next scan
                seen.add(str(f))
                process(graph, f, a.job_id, a.lang)
            if not a.watch:
                if not new:
                    print(f"No CVs to process in {folder} for job '{a.job_id}'.")
                break
            time.sleep(a.interval)
    except KeyboardInterrupt:
        print("Stopped.")
 
 
if __name__ == "__main__":
    main()