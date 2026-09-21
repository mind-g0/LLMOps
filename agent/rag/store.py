"""Qdrant access. Fixes vs. the original: one shared client (local mode locks the folder, so it must
not be opened/closed per call), deterministic point ids (re-ingest is idempotent), job lookup by
`job_id` PAYLOAD FILTER instead of similarity search, and full structured requirements stored as a
'spec' point next to the text chunks."""
import time
import uuid
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, FieldCondition, Filter, FilterSelector, MatchValue, PayloadSchemaType, PointStruct, VectorParams,
)

from agent.state import CandidateProfile, JobChunk, JobRequirement
from config import settings as S
from rag.embedder import embed

_client: Optional[QdrantClient] = None
_NS = uuid.UUID("6f1c2a52-3b1e-4a55-9d0e-2f1f6f3b7a10")


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        if S.QDRANT_URL:
            _client = QdrantClient(url=S.QDRANT_URL, api_key=S.QDRANT_API_KEY or None)
        else:
            S.QDRANT_PATH.mkdir(parents=True, exist_ok=True)
            _client = QdrantClient(path=str(S.QDRANT_PATH))
    return _client


def reset_client() -> None:
    global _client
    if _client is not None:
        _client.close()
    _client = None


def _pid(*parts: str) -> str:
    return str(uuid.uuid5(_NS, "|".join(parts)))


def _eq(key: str, value: str) -> FieldCondition:
    return FieldCondition(key=key, match=MatchValue(value=value))


def ensure_collection(name: str, keyword_indexes: tuple[str, ...] = ()) -> None:
    c = get_client()
    if not c.collection_exists(name):
        c.create_collection(name, vectors_config=VectorParams(size=S.EMBEDDING_DIM, distance=Distance.COSINE))
    if not S.QDRANT_URL:  # embedded mode ignores payload indexes (and warns)
        return
    for field in keyword_indexes:
        try:
            c.create_payload_index(name, field, PayloadSchemaType.KEYWORD)
        except Exception:
            pass  # already exists


# ── Jobs ───────────────────────────────────────────────────────────────────
def upsert_job(req: JobRequirement, chunks: list[JobChunk]) -> int:
    ensure_collection(S.JOBS_COLLECTION, ("job_id", "type"))
    c = get_client()
    c.delete(S.JOBS_COLLECTION, points_selector=FilterSelector(filter=Filter(must=[_eq("job_id", req.job_id)])))

    spec_text = " ; ".join([req.title, *req.required_skills, *req.nice_to_have_skills])
    texts = [spec_text] + [f"{ch.section}\n{ch.text}" for ch in chunks]
    vecs = embed(texts)
    base = {"job_id": req.job_id, "job_version": req.job_version, "language": req.language}

    points = [PointStruct(id=_pid(req.job_id, "spec"), vector=vecs[0].tolist(),
                          payload={**base, "type": "spec", "requirement": req.model_dump()})]
    for i, ch in enumerate(chunks):
        points.append(PointStruct(id=_pid(req.job_id, "chunk", str(i)), vector=vecs[i + 1].tolist(),
                                  payload={**base, "type": "chunk", "section": ch.section, "text": ch.text}))
    c.upsert(S.JOBS_COLLECTION, points=points)
    return len(points)


def get_job(job_id: str) -> Optional[tuple[JobRequirement, list[JobChunk]]]:
    """Exact lookup by tag. Returns None if the job is not ingested (caller must fail loudly)."""
    c = get_client()
    if not c.collection_exists(S.JOBS_COLLECTION):
        return None
    pts, _ = c.scroll(S.JOBS_COLLECTION, scroll_filter=Filter(must=[_eq("job_id", job_id)]),
                      limit=256, with_payload=True, with_vectors=False)
    spec, chunks = None, []
    for p in sorted(pts, key=lambda x: str(x.id)):
        pl = p.payload or {}
        if pl.get("type") == "spec":
            spec = JobRequirement(**pl["requirement"])
        elif pl.get("type") == "chunk":
            chunks.append(JobChunk(section=pl.get("section", ""), text=pl.get("text", "")))
    return (spec, chunks) if spec else None


# -- Candidate profile index ------------------------------------------------
def _candidate_text(profile: CandidateProfile) -> str:
    parts = [profile.name, profile.location, " ".join(profile.skills)]
    parts += [f"{x.title} {x.company} {x.description}" for x in profile.experience]
    parts += [f"{x.name} {x.description} {' '.join(x.technologies)}" for x in profile.projects]
    parts += [f"{x.degree} {x.field_of_study} {x.institution}" for x in profile.education]
    parts += [f"{x.title} {x.issuer}" for x in profile.certifications]
    return "\n".join(part for part in parts if part.strip())


def upsert_candidate(profile: CandidateProfile) -> None:
    """Index one validated profile; repeated ingestion replaces the same candidate."""
    ensure_collection(S.CANDIDATES_COLLECTION, ("candidate_id", "language"))
    point = PointStruct(
        id=_pid("candidate", profile.candidate_id),
        vector=embed([_candidate_text(profile)])[0].tolist(),
        payload={"candidate_id": profile.candidate_id, "profile": profile.model_dump(),
                 "language": profile.dominant_language, "experience_years": profile.experience_years,
                 "skills": profile.skills},
    )
    get_client().upsert(S.CANDIDATES_COLLECTION, points=[point])


def search_candidates(query: str, k: int | None = None) -> list[dict]:
    """Return a bounded retrieval shortlist; this is not a hiring decision."""
    c = get_client()
    if not c.collection_exists(S.CANDIDATES_COLLECTION):
        return []
    limit = k or S.MATCH_TOP_K
    res = c.query_points(S.CANDIDATES_COLLECTION, query=embed([query])[0].tolist(), limit=limit,
                         with_payload=True)
    return [{"retrieval_score": float(p.score), **(p.payload or {})} for p in res.points]


# ── Course catalog (optional collection) ───────────────────────────────────
def search_catalog(query: str, k: int = 3) -> list[dict]:
    c = get_client()
    if not c.collection_exists(S.CATALOG_COLLECTION):
        return []
    res = c.query_points(S.CATALOG_COLLECTION, query=embed([query])[0].tolist(), limit=k, with_payload=True)
    return [{"score": float(p.score), **(p.payload or {})} for p in res.points]


# ── Web-search cache (kept from the weather agent: never pay for the same search twice) ──
def cache_get(query: str) -> Optional[str]:
    c = get_client()
    if not c.collection_exists(S.WEB_CACHE_COLLECTION):
        return None
    res = c.query_points(S.WEB_CACHE_COLLECTION, query=embed([query])[0].tolist(), limit=1, with_payload=True)
    if not res.points:
        return None
    p = res.points[0]
    age_days = (time.time() - float((p.payload or {}).get("cached_at", 0))) / 86400
    if p.score >= S.WEB_CACHE_MIN_SIM and age_days <= S.WEB_CACHE_TTL_DAYS:
        return (p.payload or {}).get("result")
    return None


def cache_put(query: str, result: str) -> None:
    ensure_collection(S.WEB_CACHE_COLLECTION)
    get_client().upsert(S.WEB_CACHE_COLLECTION, points=[PointStruct(
        id=_pid("cache", query), vector=embed([query])[0].tolist(),
        payload={"query": query, "result": result, "cached_at": time.time()})])
