from __future__ import annotations

import json
import os
import time
import uuid
import torch.cuda
import torch
from fastapi import FastAPI, HTTPException, Depends, Security, status
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import StreamingResponse
from transformers import AutoModelForCausalLM, AutoTokenizer
from dotenv import load_dotenv
from pathlib import Path
from app.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    HealthResponse,
    ModelCard,
    ModelList,
    ResponseMessage,
    Usage,
)

load_dotenv()
SERVING_API_KEY = os.environ.get("SERVING_API_KEY")
MODEL_ID = os.environ.get("MODEL_ID")
MODEL_PATH = os.environ.get("MODEL_PATH")
HF_TOKEN = os.environ.get("API_KEY")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using {DEVICE} for model inference...")
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, token=HF_TOKEN)

# Use device_map to load the model directly to the correct device
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    token=HF_TOKEN,
    device_map=DEVICE,  # This replaces the need for model.to(DEVICE)
)
app = FastAPI(title="serving-stack", version="wk2")


REGISTRY_PATH = os.environ.get("REGISTRY_PATH", Path(__file__).parent / "registry.json")
with open(REGISTRY_PATH) as f:
    REGISTRY = json.load(f)

model.eval()
print("Model ready")

def get_api_key(api_key: str = Security(api_key_header)):
    expected = os.environ.get("SERVING_API_KEY")
    if expected is None:
        raise HTTPException(status_code=500, detail="server API key not configured")
    if not api_key or api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
            headers={"WWW-Authenticate": "API Key"},
        )
    return api_key


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", model=MODEL_ID)

@app.get("/registry")
def list_models():
    return {"models": list(REGISTRY.keys())}

@app.get("/registry/{name}")
def get_model(name: str):
    if name not in REGISTRY:
        raise HTTPException(status_code=404, detail=f"no such model: {name}")
    return REGISTRY[name]

@app.get("/v1/models", response_model=ModelList)
def list_models() -> ModelList:
    return ModelList(
        data=[
            ModelCard(id=MODEL_ID, created=int(time.time()), owned_by="aidc")
        ]
    )


def _build_inputs(req: ChatCompletionRequest):
    messages = [m.model_dump() for m in req.messages]

    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
    )

    input_ids = inputs["input_ids"].to(DEVICE)

    return input_ids, input_ids.shape[1]


def _generate(input_ids, req: ChatCompletionRequest):
    with torch.no_grad():
        out = model.generate(
            input_ids=input_ids,
            attention_mask=torch.ones_like(input_ids),
            max_new_tokens=req.max_tokens,
            do_sample=req.temperature > 0,
            temperature=(req.temperature if req.temperature > 0 else None),
            pad_token_id=tokenizer.eos_token_id,
        )

    return out[0][input_ids.shape[1] :]


@app.post("/v1/chat/completions", response_model=None)
def chat_completions(req: ChatCompletionRequest, api_key: str = Depends(get_api_key)):
    if req.model != MODEL_ID:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": (f"model '{req.model}' not found"),
                    "type": "invalid_request_error",
                    "code": "model_not_found",
                }
            },
        )

    input_ids, prompt_tokens = _build_inputs(req)

    if req.stream:
        return _stream(input_ids, prompt_tokens, req)

    new_tokens = _generate(input_ids, req)

    completion_tokens = int(new_tokens.shape[0])

    text = tokenizer.decode(new_tokens, skip_special_tokens=True)

    return ChatCompletionResponse(
        id="chatcmpl-" + uuid.uuid4().hex,
        created=int(time.time()),
        model=req.model,
        choices=[
            Choice(
                index=0,
                message=ResponseMessage(role="assistant", content=text),
                finish_reason=(
                    "length" if completion_tokens >= req.max_tokens else "stop"
                ),
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=(prompt_tokens + completion_tokens),
        ),
    )


@app.get("/registry")
def list_models():
    return {"models": list(REGISTRY.keys())}


@app.get("/registry/{name}")
def get_model(name: str):
    if name not in REGISTRY:
        raise HTTPException(status_code=404, detail=f"no such model: {name}")
    return REGISTRY[name]


def _stream(input_ids, prompt_tokens: int, req: ChatCompletionRequest):
    new_tokens = _generate(input_ids, req)

    cid = "chatcmpl-" + uuid.uuid4().hex
    created = int(time.time())

    def chunk(delta: dict, finish=None):
        payload = {
            "id": cid,
            "object": "chat.completion.chunk",
            "created": created,
            "model": req.model,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }

        return "data: " + json.dumps(payload) + "\n\n"

    def events():
        yield chunk({"role": "assistant", "content": ""})

        for tok in new_tokens:
            piece = tokenizer.decode([tok], skip_special_tokens=True)

            if piece:
                yield chunk({"content": piece})

        yield chunk({}, finish="stop")

        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
