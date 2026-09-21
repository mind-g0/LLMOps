from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ReviewStatus = Literal["approved", "not_approved", "needs_human_review"]


class SingleRouteRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    task_type: str | None = None
    payload: dict[str, Any] | None = None

    def route_payload(self) -> tuple[str, dict[str, Any]]:
        if self.payload is not None:
            return self.task_type or "llm", dict(self.payload)

        body = self.model_dump(exclude={"task_type", "payload"}, exclude_none=True)
        return self.task_type or "llm", body


class JobRequirementCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    requirements: list[str] = Field(default_factory=list)


class JobRequirementUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    requirements: list[str] | None = None
    active: bool | None = None


class JobRequirementResponse(JobRequirementCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    active: bool
    created_at: datetime
    updated_at: datetime


class CVReviewUpdate(BaseModel):
    status: ReviewStatus
    rejection_reason: str | None = None


class CVReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cv_name: str
    approved: bool
    status: ReviewStatus
    rejection_reason: str | None
    cv_object_key: str
    content_type: str | None
    job_requirement_id: UUID | None
    job_requirement_snapshot: dict | None
    rag_summary: str | None
    strengths: list[str]
    missing_requirements: list[str]
    match_score: float | None
    created_at: datetime


class CVReviewListResponse(BaseModel):
    items: list[CVReviewResponse]
    page: int
    page_size: int
    total: int
