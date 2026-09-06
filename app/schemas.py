from __future__ import annotations

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage] = Field(..., min_length=1)
    max_tokens: Optional[int] = Field(default=256, ge=1, le=4096)
    temperature: Optional[float] = Field(default=1.0, ge=0.0, le=2.0)
    stream: Optional[bool] = False
    tools: Optional[list[dict]] = None

    @field_validator("messages")
    @classmethod
    def last_message_must_be_user_or_system(cls, v):
        if v and v[-1].role == "assistant":
            raise ValueError(
                "the last message must be from 'user' or 'system', not 'assistant'"
            )
        return v


class ResponseMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class Choice(BaseModel):
    index: int = 0
    message: ResponseMessage
    finish_reason: Literal["stop", "length"] = "stop"


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage


class ModelCard(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str = "aidc"


class ModelList(BaseModel):
    object: Literal["list"] = "list"
    data: List[ModelCard]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    model: str
