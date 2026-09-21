"""Wire test: real DSPy -> litellm -> HTTP against a mock OpenAI-compatible server that returns
schema-valid JSON. Proves signatures, guided-JSON schemas, image parts, enums and ReAct tool calls
work end to end without a GPU."""
import base64
import io
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from PIL import Image

from agent.dspy_setup import get_lm
from config import settings as S

REQUESTS: list[dict] = []


def _fill(schema, root):
    """Build a minimal valid value for a JSON schema."""
    if "$ref" in schema:
        return _fill(root["$defs"][schema["$ref"].split("/")[-1]], root)
    if "enum" in schema:
        return schema["enum"][0]
    if "anyOf" in schema:
        nn = [s for s in schema["anyOf"] if s.get("type") != "null"]
        return _fill(nn[0], root) if nn else None
    t = schema.get("type")
    if t == "object":
        return {k: _fill(v, root) for k, v in schema.get("properties", {}).items()}
    if t == "array":
        return []
    if t == "string":
        return "sample"
    if t in ("number", "integer"):
        return 1
    if t == "boolean":
        return False
    return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        REQUESTS.append(body)
        payload = body["payload"]  # gateway envelope: {"task_type", "payload": {...chat body...}}
        rf = payload.get("response_format") or {}
        schema = (rf.get("json_schema") or {}).get("schema") or {}
        if schema:
            content = json.dumps(_fill(schema, schema))
        elif "next_tool_name" in json.dumps(payload["messages"]):  # ReAct step (json_object mode)
            n = sum(1 for r in REQUESTS if "next_tool_name" in json.dumps(r["payload"]["messages"]))
            tool = "search_cv" if "search_cv" in json.dumps(payload["messages"]) else "web_search"
            step = ({"next_tool_name": tool, "next_tool_args": {"query": "kubernetes"}}
                    if n == 1 else {"next_tool_name": "finish", "next_tool_args": {}})
            content = json.dumps({"next_thought": "t", **step})
        else:
            content = "{}"
        resp = {"id": "x", "object": "chat.completion", "created": 0, "model": payload.get("model", "m"),
                "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
        data = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def mock_server(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}/v1"
    monkeypatch.setattr(S, "VLM_API_BASE", base)
    monkeypatch.setattr(S, "LLM_API_BASE", base)
    get_lm.cache_clear()
    REQUESTS.clear()
    yield
    srv.shutdown()
    get_lm.cache_clear()


def test_extraction_sends_images_and_gets_a_typed_profile(mock_server, tmp_path):
    from agent.nodes.extractor import _call_extract

    img = tmp_path / "p.png"
    Image.new("RGB", (64, 64), "white").save(img)
    ext = _call_extract(True, [str(img)], "")
    assert ext.name == "sample"  # parsed into CandidateExtraction, not a raw string
    rf = REQUESTS[-1]["response_format"]
    assert rf["type"] == "json_schema", "guided decoding needs the schema, not plain json_object"
    assert "name" in rf["json_schema"]["schema"]["$defs"]["CandidateExtraction"]["properties"]
    parts = REQUESTS[-1]["messages"][-1]["content"]
    assert any(p.get("type") == "image_url" for p in parts), "page image must reach the VLM"
    assert REQUESTS[-1]["model"] == S.VLM_MODEL
    assert "chat_template_kwargs" not in REQUESTS[-1].get("extra_body", {})  # thinking model: no toggle


def test_text_extraction_and_llm_thinking_disabled(mock_server):
    from agent.nodes.extractor import _call_extract

    _call_extract(False, [], "some cv text")
    assert REQUESTS[-1]["model"] == S.VLM_MODEL  # TEXT_EXTRACTION_MODEL default = vlm
    from agent.nodes.matcher import _call_assess

    rel, edu, proj = _call_assess("Engineer", "summary", "brief")
    assert rel in ("strong", "partial", "weak") and edu in ("meets", "related", "unrelated", "not_required")
    body = REQUESTS[-1]
    assert body["model"] == S.LLM_MODEL
    assert body["chat_template_kwargs"] == {"enable_thinking": False} or \
        body.get("extra_body", {}).get("chat_template_kwargs") == {"enable_thinking": False}


def test_react_agent_runs_a_tool_loop_and_discards_unverified_urls(mock_server, monkeypatch):
    from agent.nodes import recommender as R

    monkeypatch.setattr(S, "RECOMMEND_MAX_ITERS", 2)
    rec = R._from_web("Kubernetes", "Backend Engineer", "en")
    assert rec is None  # mock URL 'sample' was never returned by a search -> discarded (anti-hallucination)
    assert len(REQUESTS) >= 3  # tool step, finish step, final extraction
    assert REQUESTS[-1]["response_format"]["type"] == "json_schema"  # final answer IS schema-constrained


def test_gap_reasoner_runs_with_thinking_on_and_tools_visible(mock_server):
    from agent.nodes.gap_agent import _call_react_judge
    from tests.conftest import fake_embed

    lines = ["Operated Kubernetes clusters", "Python developer"]
    seen: list[str] = []
    verdict, quote = _call_react_judge("Kubernetes", lines, fake_embed(lines), [], seen, "")
    assert verdict in ("met", "partial", "missing")
    assert seen, "the agent's search_cv tool must have been executed"
    body = REQUESTS[0]
    kw = body.get("chat_template_kwargs") or body.get("extra_body", {}).get("chat_template_kwargs")
    assert kw == {"enable_thinking": True}
    assert body["model"] == S.LLM_MODEL  # same served model as the non-thinking calls
