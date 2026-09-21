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


class JobRequirementSpec(BaseModel):
    """Structured job spec for the agent — maps backend fields to what the agent's
    JobRequirement model expects."""

    job_id: str
    name: str
    title: str
    description: str
    required_skills: list[str]
    created_at: datetime

    @classmethod
    def from_orm_job(cls, job: Any) -> "JobRequirementSpec":
        return cls(
            job_id=str(job.id),
            name=job.name,
            title=job.title,
            description=job.description,
            required_skills=job.requirements or [],
            created_at=job.created_at,
        )


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
    rag_summary: str | None = None
    strengths: list[str] | None = None
    missing_requirements: list[str] | None = None
    match_score: float | None = None


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