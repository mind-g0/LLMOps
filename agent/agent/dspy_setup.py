"""DSPy wiring. One place decides which model a node talks to and how outputs are forced.

All models are reached through ONE gateway (S.LLM_API_BASE / S.VLM_API_BASE, ending in /v1). It takes a wrapped body
    {"task_type": "llm" | "ocr", "payload": {...normal chat-completions body...}}
and answers with a normal OpenAI chat.completion JSON. LiteLLM cannot send that body shape, so
GatewayLM posts it directly and converts the answer back into a litellm ModelResponse for DSPy.

  kind      -> task_type   (which model the gateway routes to)
  "llm"        "llm"       Qwen3.5-9B, thinking follows LLM_ENABLE_THINKING
  "reasoner"   "llm"       same model, thinking ON
  "ocr"        "ocr"       Qwen3-VL-8B-Instruct

Structured output: JSONAdapter asks for a Pydantic schema as `response_format`; it is converted to a
JSON-schema dict and placed inside `payload`, so vLLM can enforce it with guided decoding.
"""
import json
import os
import time
from functools import lru_cache
from typing import Any, Literal

import dspy
import httpx
import litellm

from agent.logger import DSPyTracer, get_logger
from config import settings as S

Kind = Literal["ocr", "llm", "reasoner"]

_TASK_TYPE = {"llm": "llm", "reasoner": "llm", "ocr": "ocr"}
_ALIASES = {"vlm": "ocr"}  # the old name still works
# GATEWAY_STREAM=1 in .env: stream every request (see _send). Use it if the gateway cuts slow answers.
_STREAM = os.getenv("GATEWAY_STREAM", "0").strip().lower() in {"1", "true", "yes", "on"}
# LM-level settings that must NOT be forwarded inside `payload`
_NON_PAYLOAD = {"api_key", "api_base", "base_url", "timeout", "num_retries", "cache",
                "rollout_id", "extra_body", "model", "headers"}


def _response_format(rf: Any) -> Any:
    """DSPy passes a Pydantic class; the gateway needs a JSON-serialisable dict."""
    if isinstance(rf, type) and hasattr(rf, "model_json_schema"):
        return {"type": "json_schema",
                "json_schema": {"name": rf.__name__, "schema": rf.model_json_schema(), "strict": True}}
    return rf


def _short(r: httpx.Response) -> str:
    """Compact error text: a Cloudflare/HTML error page becomes one readable line."""
    text = r.text.strip()
    if text.startswith("<"):
        return f"HTML error page (cf-ray={r.headers.get('cf-ray')})"
    return text[:300]


def _send(url: str, body: dict, headers: dict, timeout: float, stream: bool) -> tuple[int, Any]:
    """POST once. Returns (status, chat.completion dict) on success, (status, short error text) otherwise.

    stream=True asks for server-sent events and stitches them back into one completion. The read
    timeout then applies between chunks instead of to the whole answer, which keeps long generations
    alive behind a gateway that gives up on slow single responses.
    """
    if not stream:
        r = httpx.post(url, json=body, headers=headers, timeout=timeout)
        return (r.status_code, r.json()) if r.status_code < 400 else (r.status_code, _short(r))

    body = {**body, "payload": {**body["payload"], "stream": True,
                                "stream_options": {"include_usage": True}}}
    parts: list[str] = []
    finish, usage, model, cid = None, {}, None, None
    with httpx.stream("POST", url, json=body, headers=headers, timeout=timeout) as r:
        if r.status_code >= 400:
            r.read()
            return r.status_code, _short(r)
        for line in r.iter_lines():
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            if "error" in chunk:
                return 502, f"stream error: {chunk['error']}"
            cid, model = chunk.get("id", cid), chunk.get("model", model)
            usage = chunk.get("usage") or usage
            for c in chunk.get("choices") or []:
                parts.append((c.get("delta") or {}).get("content") or "")
                finish = c.get("finish_reason") or finish
    return 200, {"id": cid, "model": model, "usage": usage,
                 "choices": [{"index": 0, "finish_reason": finish or "stop",
                              "message": {"role": "assistant", "content": "".join(parts)}}]}


def _to_model_response(data: dict) -> litellm.ModelResponse:
    """Keep only the standard OpenAI fields; drop vLLM extras (token_ids, routed_experts, ...)."""
    choices = []
    for c in data.get("choices", []):
        m = c.get("message") or {}
        choices.append({
            "index": c.get("index", 0),
            "finish_reason": c.get("finish_reason") or "stop",
            "message": {"role": m.get("role", "assistant"), "content": m.get("content")},
        })
    u = data.get("usage") or {}
    return litellm.ModelResponse(
        id=data.get("id"), created=data.get("created"), model=data.get("model"), choices=choices,
        usage=litellm.Usage(prompt_tokens=u.get("prompt_tokens", 0),
                            completion_tokens=u.get("completion_tokens", 0),
                            total_tokens=u.get("total_tokens", 0)),

    )


class GatewayLM(dspy.LM):
    """dspy.LM that talks to the gateway with the {"task_type", "payload"} body.

    supports_response_schema is declared True: litellm does not know self-hosted model names, so DSPy
    would silently downgrade to plain `json_object` mode. vLLM DOES enforce a JSON schema, so we say so.
    Note: signatures with open-ended dict outputs (ReAct's tool args) still use json_object mode.
    """

    def __init__(self, model: str, task_type: str, **kwargs):
        super().__init__(model, **kwargs)
        self.task_type = task_type

    @property
    def supports_response_schema(self) -> bool:
        return True

    def forward(self, prompt=None, messages=None, **kwargs):
        merged = {**self.kwargs, **kwargs}
        payload = {k: v for k, v in merged.items() if k not in _NON_PAYLOAD and v is not None}
        payload.update(merged.get("extra_body") or {})          # e.g. chat_template_kwargs
        if "response_format" in payload:
            payload["response_format"] = _response_format(payload["response_format"])
        payload["messages"] = messages or [{"role": "user", "content": prompt}]

        body = {"task_type": self.task_type, "payload": payload}
        headers = {"Authorization": f"Bearer {merged.get('api_key') or S.API_KEY}"}
        timeout = merged.get("timeout", S.LM_TIMEOUT)
        retries = getattr(self, "num_retries", 2) or 0

        base = str(merged["api_base"]).rstrip("/")             # e.g. https://llmops-api.is-3.net/v1
        url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"

        last: Exception | None = None
        for attempt in range(retries + 1):
            try:
                status, out = _send(url, body, headers, timeout, _STREAM)
            except httpx.TransportError as e:
                last = e
            else:
                if status >= 500 or status == 429:                 # transient: retry
                    last = RuntimeError(f"gateway {status}: {out}")
                elif status >= 400:                                # our fault: do not retry
                    raise RuntimeError(f"gateway {status}: {out}")
                else:
                    resp = _to_model_response(out)
                    if any(c.finish_reason == "length" for c in resp.choices):
                        get_logger().warning(f"[{self.task_type}] output truncated "
                                             f"(finish_reason=length); raise max_tokens")
                    return resp
            if attempt < retries:                                  # no pointless wait after the last try
                time.sleep(3 * (attempt + 1))
        raise RuntimeError(f"gateway failed after {retries + 1} attempts: {last}")


def get_lm(kind: Kind) -> dspy.LM:
    """Kinds: "llm", "reasoner", "ocr" ("vlm" is accepted as an alias of "ocr")."""
    return _get_lm(_ALIASES.get(kind, kind))


@lru_cache(maxsize=None)
def _get_lm(kind: str) -> dspy.LM:
    """One LM per kind. The model string is used only for logging/tracing; the gateway picks the
    real model from task_type."""
    if kind not in _TASK_TYPE:
        raise ValueError(f"unknown LM kind: {kind!r}")
    common = dict(api_key=S.API_KEY, timeout=S.LM_TIMEOUT, num_retries=2, cache=S.DSPY_CACHE)

    if kind == "ocr":
        return GatewayLM(f"openai/{S.VLM_MODEL}", "ocr", api_base=S.VLM_API_BASE,
                         temperature=S.VLM_TEMPERATURE, max_tokens=S.VLM_MAX_TOKENS, **common)
    if kind == "reasoner":  # same model as "llm", thinking enabled per request
        return GatewayLM(f"openai/{S.LLM_MODEL}", "llm", api_base=S.LLM_API_BASE,
                         temperature=S.REASONER_TEMPERATURE, max_tokens=S.REASONER_MAX_TOKENS,
                         extra_body={"chat_template_kwargs": {"enable_thinking": True}}, **common)
    return GatewayLM(f"openai/{S.LLM_MODEL}", "llm", api_base=S.LLM_API_BASE,
                     temperature=S.LLM_TEMPERATURE, max_tokens=S.LLM_MAX_TOKENS,
                     extra_body={"chat_template_kwargs": {"enable_thinking": S.LLM_ENABLE_THINKING}},
                     **common)


get_lm.cache_clear = _get_lm.cache_clear  # type: ignore[attr-defined]


def lm_ctx(kind: Kind):
    """Context manager: `with lm_ctx("llm"): dspy.Predict(Sig)(...)`.

    Scoped (not global) so parallel LangGraph branches / worker threads never fight over settings.
    """
    return dspy.context(lm=get_lm(kind), adapter=dspy.JSONAdapter())


def init_dspy() -> None:
    """Call once from the main thread."""
    dspy.configure(callbacks=[DSPyTracer()])