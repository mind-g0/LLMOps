"""Pipeline logger (same structure as the weather agent), rebuilt for DSPy.

  * @log_node        - times a node, logs a PII-safe state snapshot, and appends the AgentStep
                       to the audit trail so nodes carry no boilerplate.
  * DSPyTracer       - DSPy BaseCallback: logs every LM call / tool call under the current node.

CVs are personal data. Unless LOG_PROMPTS=true, prompts and completions are NOT written to logs;
only sizes, latency and tool names are.
"""
import contextvars
import json
import logging
import textwrap
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Optional

from dspy.utils.callback import BaseCallback

from agent.state import AgentStep, RDEMError
from config import settings as S

_current_node: contextvars.ContextVar[str] = contextvars.ContextVar("current_node", default="-")
_LOGGER_NAME = "hr_agent"


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)


def init_run(run_id: Optional[str] = None) -> str:
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    S.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = get_logger()
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False
    fmt = logging.Formatter("[%(asctime)s] %(levelname)-5s | %(message)s", datefmt="%H:%M:%S")
    for h in (logging.StreamHandler(), logging.FileHandler(S.LOG_DIR / f"run_{run_id}.log", encoding="utf-8")):
        h.setLevel(logging.DEBUG)
        h.setFormatter(fmt)
        logger.addHandler(h)
    logger.info("=" * 80)
    logger.info(f"  RUN {run_id}  |  log_prompts={S.LOG_PROMPTS}")
    logger.info("=" * 80)
    return run_id


def _trunc(text: Any, n: int = 1200) -> str:
    text = str(text)
    return text if len(text) <= n else text[:n] + f"... [{len(text)} chars]"


def _indent(text: str) -> str:
    return textwrap.indent(text, "        ")


class DSPyTracer(BaseCallback):
    """Register once: dspy.configure(callbacks=[DSPyTracer()])."""

    def __init__(self) -> None:
        super().__init__()
        self._starts: dict[str, float] = {}

    # LM calls ---------------------------------------------------------------
    def on_lm_start(self, call_id, instance, inputs):
        self._starts[call_id] = time.perf_counter()
        node = _current_node.get()
        model = getattr(instance, "model", "?")
        msgs = inputs.get("messages") or []
        get_logger().debug(f"    [{node}] LM call -> {model} ({len(msgs)} messages)")
        if S.LOG_PROMPTS:
            for m in msgs:
                content = m.get("content", "")
                if isinstance(content, list):  # multimodal: never dump image bytes
                    content = " ".join(p.get("text", "<image>") if p.get("type") == "text" else "<image>" for p in content)
                get_logger().debug(f"      {m.get('role', '?').upper()}:\n{_indent(_trunc(content))}")

    def on_lm_end(self, call_id, outputs, exception=None):
        node = _current_node.get()
        dt = time.perf_counter() - self._starts.pop(call_id, time.perf_counter())
        if exception:
            get_logger().warning(f"    [{node}] LM call FAILED after {dt:.1f}s: {type(exception).__name__}: {exception}")
            return
        get_logger().debug(f"    [{node}] LM done in {dt:.1f}s")
        if S.LOG_PROMPTS and outputs:
            get_logger().debug(f"      OUTPUT:\n{_indent(_trunc(outputs))}")

    # Tool calls (ReAct) -----------------------------------------------------
    def on_tool_start(self, call_id, instance, inputs):
        self._starts[call_id] = time.perf_counter()
        name = getattr(instance, "name", type(instance).__name__)
        # tool arguments are skill names / search queries, not CV content
        get_logger().debug(f"    [{_current_node.get()}] TOOL {name}({_trunc(json.dumps(inputs, ensure_ascii=False, default=str), 300)})")

    def on_tool_end(self, call_id, outputs, exception=None):
        dt = time.perf_counter() - self._starts.pop(call_id, time.perf_counter())
        status = f"ERROR {exception}" if exception else f"ok, {len(str(outputs))} chars"
        get_logger().debug(f"    [{_current_node.get()}] TOOL result in {dt:.1f}s ({status})")


def _snapshot(state) -> dict:
    """Key state fields WITHOUT personal data (no name/contact/CV text)."""
    snap: dict[str, Any] = {"cv": getattr(state, "cv_path", "")[-40:], "job_id": state.job_id}
    if state.profile:
        p = state.profile
        snap["profile"] = (
            f"lang={p.detected_language} method={p.parse_method} skills={len(p.skills)} "
            f"years={p.experience_years} conf={p.raw_parse_confidence:.2f}"
        )
    if state.skill_gap:
        snap["gap"] = f"missing={len(state.skill_gap.missing_skills)} partial={len(state.skill_gap.partial_skills)}"
    if state.match:
        snap["match"] = f"score={state.match.match_score} conf={state.match.match_confidence} bucket={state.match.triage_bucket}"
    snap["attempts"] = state.extract_attempts
    snap["errors"] = len(state.global_error_log)
    return snap


def log_node(func):
    """Decorator for graph nodes. Nodes may return '_status' ('success' by default)."""

    @wraps(func)
    def wrapper(state):
        logger = get_logger()
        name = func.__name__
        token = _current_node.set(name)
        t0 = time.perf_counter()
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"  >>> ENTER  {name}")
        for k, v in _snapshot(state).items():
            logger.debug(f"    {k}: {v}")
        try:
            result = func(state) or {}
        except Exception as exc:
            logger.error(f"  [{name}] EXCEPTION after {time.perf_counter() - t0:.1f}s: {type(exc).__name__}: {exc}")
            raise
        finally:
            _current_node.reset(token)

        elapsed = time.perf_counter() - t0
        status = result.pop("_status", "success")
        errors: list[RDEMError] = result.get("global_error_log", [])
        result["audit_trail"] = [
            AgentStep(node_name=name, status=status, error=errors[0] if errors else None, duration_s=round(elapsed, 2))
        ]
        logger.info(f"  <<< EXIT   {name}  ({elapsed:.1f}s) status={status}")
        for e in errors:
            logger.warning(f"    RDEM[{e.error_type}] {e.message} | suggestion: {e.suggestion}")
        return result

    return wrapper
