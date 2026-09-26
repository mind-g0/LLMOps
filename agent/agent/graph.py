"""Graph wiring. Routing is done by small pure functions (no orchestrator LLM, no orchestrator hop).

  START -> retriever -> converter -> parser -> extractor -> validator -+-> extractor   (escalate to vision)
                                                                       +-> gap_analyzer -> matcher -+-> recommender -> formatter
                                                                       |                             +-> formatter
                                                                       +-> formatter (failed)
Any failure short-circuits to the formatter, which always emits a structured report.
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from agent.nodes.converter import converter
from agent.nodes.extractor import extractor
from agent.nodes.formatter import formatter
from agent.nodes.gap_agent import gap_agent
from agent.nodes.matcher import matcher
from agent.nodes.parser import parser
from agent.nodes.recommender import recommender
from agent.nodes.retriever import retriever
from agent.nodes.validator import validator
from agent.state import HRState
from config import settings as S

_TRANSIENT = {"APIConnectionError", "APITimeoutError", "Timeout", "ServiceUnavailableError",
              "RateLimitError", "InternalServerError", "ConnectError", "ReadTimeout"}


def _is_transient(exc: Exception) -> bool:
    """Retry infrastructure hiccups only. (The weather agent's retry_on included `Exception`,
    which retries deterministic bugs too and wastes GPU time.)"""
    return isinstance(exc, (ConnectionError, TimeoutError)) or type(exc).__name__ in _TRANSIENT


_retry = RetryPolicy(max_attempts=3, initial_interval=1.0, backoff_factor=2.0, retry_on=_is_transient)


def _failed_or(next_node: str):
    return lambda s: "formatter" if s.status == "failed" else next_node


def after_validator(s: HRState) -> str:
    if s.status == "failed":
        return "formatter"
    return "extractor" if s.retry_extract else "gap_analyzer"


def after_matcher(s: HRState) -> str:
    g = s.skill_gap
    return "recommender" if (S.ENABLE_RECOMMENDATIONS and g and (g.missing_skills or g.partial_skills)) else "formatter"


def build_graph():
    b = StateGraph(HRState)
    b.add_node("retriever", retriever, retry_policy=_retry)
    b.add_node("converter", converter)
    b.add_node("parser", parser)
    b.add_node("extractor", extractor)
    b.add_node("validator", validator)
    b.add_node("gap_analyzer", gap_agent)
    b.add_node("matcher", matcher)
    b.add_node("recommender", recommender, retry_policy=_retry)
    b.add_node("formatter", formatter)

    b.add_edge(START, "retriever")
    b.add_conditional_edges("retriever", _failed_or("converter"), ["converter", "formatter"])
    b.add_conditional_edges("converter", _failed_or("parser"), ["parser", "formatter"])
    b.add_conditional_edges("parser", _failed_or("extractor"), ["extractor", "formatter"])
    b.add_edge("extractor", "validator")
    b.add_conditional_edges("validator", after_validator, ["extractor", "gap_analyzer", "formatter"])
    b.add_edge("gap_analyzer", "matcher")
    b.add_conditional_edges("matcher", after_matcher, ["recommender", "formatter"])
    b.add_edge("recommender", "formatter")
    b.add_edge("formatter", END)
    return b.compile(checkpointer=MemorySaver())
