"""Recommendation agent. Catalog first (cheap, deterministic); only when the catalog has no good
coverage does a ReAct agent search the web with Tavily. It sees the skill name and job title only:
never any candidate data."""
import contextvars
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import dspy

from agent.dspy_setup import lm_ctx
from agent.logger import get_logger, log_node
from agent.signatures import RecommendResource, WriteReason
from agent.state import HRState, Recommendation
from agent.tools.search_tools import make_web_search
from config import settings as S
from rag import store
from utils.text import language_matches


def pick_skills(state: HRState) -> list[str]:
    v = state.skill_gap.verdicts
    ordered = ([x.skill for x in v if x.importance == "required" and x.verdict == "missing"]
               + [x.skill for x in v if x.importance == "required" and x.verdict == "partial"]
               + [x.skill for x in v if x.importance == "nice" and x.verdict == "missing"])
    return list(dict.fromkeys(ordered))[: S.MAX_RECOMMEND_SKILLS]


def _call_reason(target: str, skill: str, title: str, desc: str) -> str:
    """Thin LLM boundary (patched in tests)."""
    with lm_ctx("llm"):
        return dspy.Predict(WriteReason)(target_language=target, skill=skill, resource_title=title,
                                         resource_description=desc).reason


def _reason_in_language(target: str, skill: str, title: str, desc: str, first: str = "") -> str:
    reason = first
    for _ in range(2):
        if reason and language_matches(reason, target):
            return reason
        reason = _call_reason(target, skill, title, desc)
    return reason


def _from_catalog(skill: str, target: str) -> Optional[Recommendation]:
    hits = store.search_catalog(skill, k=3)
    if not hits or hits[0]["score"] < S.CATALOG_MIN_SCORE:
        return None
    # prefer the target language but never hard-exclude (an English course beats nothing)
    hits.sort(key=lambda h: (h.get("language") == target, h["score"]), reverse=True)
    h = hits[0]
    desc = h.get("description_ar") if target == "ar" and h.get("description_ar") else h.get("description", "")
    return Recommendation(missing_skill=skill, title=h.get("title", ""), provider=h.get("provider", ""),
                          url=h.get("url", ""), source="catalog",
                          reason=_reason_in_language(target, skill, h.get("title", ""), desc))


def _from_web(skill: str, job_title: str, target: str) -> Optional[Recommendation]:
    seen: set[str] = set()
    with lm_ctx("llm"):
        agent = dspy.ReAct(RecommendResource, tools=[make_web_search(seen)], max_iters=S.RECOMMEND_MAX_ITERS)
        pred = agent(skill=skill, job_title=job_title, target_language=target)
    norm = lambda u: u.strip().rstrip("/")  # noqa: E731
    url = norm(pred.url or "")
    if not url or url not in {norm(u) for u in seen}:  # URL must come from a real search result
        get_logger().warning(f"    [recommender] '{skill}': URL not from search results; discarded")
        return None
    return Recommendation(missing_skill=skill, title=pred.title, provider=pred.provider, url=pred.url,
                          source="web_search",
                          reason=_reason_in_language(target, skill, pred.title, "", first=pred.reason))


def recommend_one(skill: str, job_title: str, target: str) -> Optional[Recommendation]:
    try:
        return _from_catalog(skill, target) or _from_web(skill, job_title, target)
    except Exception as e:
        get_logger().warning(f"    [recommender] '{skill}' failed: {type(e).__name__}: {str(e)[:200]}")
        return None


@log_node
def recommender(state: HRState) -> dict:
    skills = pick_skills(state)
    title, target = state.job.requirement.title, state.target_language
    with ThreadPoolExecutor(max_workers=S.RECOMMEND_WORKERS) as ex:
        futures = [ex.submit(contextvars.copy_context().run, recommend_one, s, title, target) for s in skills]
        results = [f.result() for f in futures]
    recs = [r for r in results if r]
    unresolved = [s for s, r in zip(skills, results) if r is None]
    return {"recommendations": recs, "unresolved_skills": unresolved}
