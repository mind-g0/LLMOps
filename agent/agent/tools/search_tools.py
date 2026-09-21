"""Tools for the recommendation agent.

Privacy: the agent only ever receives an abstract skill name and job title, never CV content. As a
second layer, every query is scrubbed of emails / phone numbers / URLs before leaving the machine.
Kept from the weather agent: cache-before-API, so identical searches cost nothing.
"""
import re
from typing import Callable

from agent.logger import get_logger
from config import settings as S
from rag import store

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?<!\d)(?:\+?\d[\s().-]?){8,15}(?!\d)")
_URL = re.compile(r"https?://\S+")


def scrub_query(q: str) -> str:
    for rx in (_EMAIL, _URL, _PHONE):
        q = rx.sub(" ", q)
    return re.sub(r"\s+", " ", q).strip()[:200]


def make_web_search(seen_urls: set[str]) -> Callable[[str], str]:
    """Factory: returns a tool that records every URL it returns, so the caller can verify that the
    final recommendation's URL really came from a search result (anti-hallucination check)."""

    def web_search(query: str) -> str:
        """Search the web for learning resources (courses, certifications, tutorials). Input: a short
        search query naming the skill, e.g. 'best Kubernetes course for beginners'. Returns numbered
        results with title, url and a snippet."""
        q = scrub_query(query)
        if not q:
            return "Empty query."
        cached = None
        try:
            cached = store.cache_get(q)
        except Exception as e:  # cache is an optimisation, never a failure
            get_logger().debug(f"    web cache lookup failed (non-fatal): {e}")
        if cached:
            seen_urls.update(re.findall(r"URL: (\S+)", cached))
            return cached
        if not S.TAVILY_API_KEY:
            return "Web search is unavailable (no API key configured)."

        from tavily import TavilyClient  # lazy

        try:
            res = TavilyClient(api_key=S.TAVILY_API_KEY).search(
                query=q, max_results=4, search_depth="basic", include_answer=False)
        except Exception as e:
            return f"Web search failed: {type(e).__name__}"
        lines = []
        for i, r in enumerate(res.get("results", []), 1):
            seen_urls.add(r.get("url", ""))
            lines.append(f"[{i}] {r.get('title', '')}\nURL: {r.get('url', '')}\n{(r.get('content') or '')[:350]}")
        out = "\n\n".join(lines) or "No results found."
        if lines:
            try:
                store.cache_put(q, out)
            except Exception as e:
                get_logger().debug(f"    web cache write failed (non-fatal): {e}")
        return out

    return web_search
