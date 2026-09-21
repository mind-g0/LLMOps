import os

import httpx  # type: ignore[import-untyped]
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas import SingleRouteRequest

load_dotenv()

router = APIRouter()

MODEL_LLM_URL = os.environ["MODEL_LLM_URL"]
MODEL_OCR_URL = os.environ["MODEL_OCR_URL"]
LLM_API_KEY = os.environ["LLM_API_KEY"]


@router.post("/v1/chat/completions")
async def route_request(request: SingleRouteRequest):
    if request.task_type == "llm":
        target_url = MODEL_LLM_URL
        headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
    elif request.task_type == "ocr":
        target_url = MODEL_OCR_URL
        headers = {}
    else:
        raise HTTPException(
            status_code=400, detail="Invalid task_type. Use 'llm' or 'ocr'."
        )

    if not target_url:
        raise HTTPException(
            status_code=503,
            detail=f"No backend URL configured for task_type '{request.task_type}'",
        )

    payload = dict(request.payload)
    try:
        async with httpx.AsyncClient() as client:
            if request.task_type == "llm" and "model" not in payload:
                models_url = (
                    target_url.removesuffix("/chat/completions") + "/models"
                )
                models_response = await client.get(models_url, headers=headers)
                models_response.raise_for_status()
                models = models_response.json().get("data", [])
                if not models:
                    raise HTTPException(
                        status_code=502,
                        detail="LLM backend returned no available models",
                    )
                payload["model"] = models[0]["id"]
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Error contacting model backend: {exc}",
        )

    if payload.get("stream"):

        async def stream_response():
            async with httpx.AsyncClient() as client:
                try:
                    async with client.stream(
                        "POST", target_url, json=payload, headers=headers
                    ) as response:
                        response.raise_for_status()
                        async for chunk in response.aiter_raw():
                            yield chunk
                except httpx.HTTPError as exc:
                    yield f'data: {{"error": "{exc}"}}\n\n'.encode()

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                target_url, json=payload, headers=headers
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Error contacting model backend: {exc}",
        )
