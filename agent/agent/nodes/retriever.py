"""Retriever node: loads the job by its unique tag. No LLM, no similarity search.

Runs FIRST so a missing/empty job fails in milliseconds instead of after GPU-heavy extraction.
"""
from agent.logger import log_node
from agent.state import HRState, JobContext, RDEMError
from rag import store


@log_node
def retriever(state: HRState) -> dict:
    try:
        found = store.get_job(state.job_id)
    except Exception as e:
        rdem = RDEMError(node="retriever", error_type="store_unavailable",
                         message=f"{type(e).__name__}: {e}", suggestion="Check the Qdrant service/path.")
        return {"status": "failed", "global_error_log": [rdem], "_status": "error"}

    if not found:
        rdem = RDEMError(node="retriever", error_type="job_not_found",
                         message=f"No job with job_id='{state.job_id}' in the vector store.",
                         suggestion="Ingest it first: python -m rag.job_ingest --dir data")
        return {"status": "failed", "global_error_log": [rdem], "_status": "error"}

    req, chunks = found
    if not req.required_skills:
        rdem = RDEMError(node="retriever", error_type="job_spec_empty",
                         message=f"Job '{state.job_id}' has no required skills.",
                         suggestion="Fix the posting and re-ingest.")
        return {"status": "failed", "global_error_log": [rdem], "_status": "error"}

    return {"job": JobContext(requirement=req, chunks=chunks)}
