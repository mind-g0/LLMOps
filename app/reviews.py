import json
import uuid
from pathlib import PurePath
from typing import Any, cast
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.db import get_db_session
from app.models import CVReview, JobRequirement
from app.schemas import (
    CVReviewListResponse,
    CVReviewResponse,
    CVReviewUpdate,
    ReviewStatus,
)
from app.storage import download_cv, get_cv_url, upload_cv

router = APIRouter(prefix="/api/v1/cv-reviews", tags=["cv-reviews"])


def status_to_approved(status: str) -> bool:
    return status == "approved"


def parse_string_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=422, detail="Expected a JSON string list"
        ) from exc
    if not isinstance(parsed, list):
        raise HTTPException(
            status_code=422, detail="Expected a JSON string list"
        )
    items = cast(list[Any], parsed)
    if not all(isinstance(item, str) for item in items):
        raise HTTPException(
            status_code=422, detail="Expected a JSON string list"
        )
    return [cast(str, item) for item in items]


@router.post("", response_model=CVReviewResponse, status_code=201)
async def create_cv_review(
    cv: UploadFile = File(...),
    approved: bool | None = Form(None),
    rejection_reason: str | None = Form(None),
    status: ReviewStatus | None = Form(None),
    job_requirement_id: UUID | None = Form(None),
    rag_summary: str | None = Form(None),
    strengths: str | None = Form(None),
    missing_requirements: str | None = Form(None),
    match_score: float | None = Form(None),
    session: AsyncSession = Depends(get_db_session),
):
    if status is None:
        if approved is None:
            raise HTTPException(
                status_code=422, detail="approved or status is required"
            )
        status = "approved" if approved else "not_approved"

    job_snapshot = None
    if job_requirement_id is not None:
        job = await session.get(JobRequirement, job_requirement_id)
        if job is None or not job.active:
            raise HTTPException(
                status_code=404, detail="Job requirement not found"
            )
        job_snapshot = {
            "id": str(job.id),
            "name": job.name,
            "title": job.title,
            "description": job.description,
            "requirements": job.requirements,
        }

    content = await cv.read()
    if not content:
        raise HTTPException(status_code=422, detail="CV file is empty")

    review_id = uuid.uuid4()
    filename = PurePath(cv.filename or "cv-upload").name
    object_key = f"cvs/{review_id}/{filename}"
    try:
        await run_in_threadpool(
            upload_cv, object_key, content, cv.content_type
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Unable to store CV in MinIO"
        ) from exc

    review = CVReview(
        id=review_id,
        cv_name=filename,
        approved=status_to_approved(status),
        status=status,
        rejection_reason=rejection_reason,
        cv_object_key=object_key,
        content_type=cv.content_type,
        job_requirement_id=job_requirement_id,
        job_requirement_snapshot=job_snapshot,
        rag_summary=rag_summary,
        strengths=parse_string_list(strengths),
        missing_requirements=parse_string_list(missing_requirements),
        match_score=match_score,
    )
    session.add(review)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(review)
    return review


@router.get("", response_model=CVReviewListResponse)
async def list_cv_reviews(
    status: ReviewStatus | None = Query(None),
    job_requirement_id: UUID | None = Query(None),
    search: str | None = Query(None, min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("newest", pattern="^(newest|oldest)$"),
    session: AsyncSession = Depends(get_db_session),
):
    filters: list[Any] = []
    if status:
        filters.append(CVReview.status == status)
    if job_requirement_id:
        filters.append(CVReview.job_requirement_id == job_requirement_id)
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                CVReview.cv_name.ilike(pattern),
                CVReview.rag_summary.ilike(pattern),
            )
        )

    count_query = select(func.count()).select_from(CVReview).where(*filters)
    total = (await session.execute(count_query)).scalar_one()
    order = (
        CVReview.created_at.desc()
        if sort == "newest"
        else CVReview.created_at.asc()
    )
    query = (
        select(CVReview)
        .where(*filters)
        .order_by(order)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(query)
    return {
        "items": result.scalars().all(),
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/{review_id}/file")
async def get_cv_file(
    review_id: UUID, session: AsyncSession = Depends(get_db_session)
):
    review = await session.get(CVReview, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="CV review not found")
    try:
        url = await run_in_threadpool(get_cv_url, review.cv_object_key)
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Unable to access CV in MinIO"
        ) from exc
    return {"url": url, "expires_in": 900}


@router.get("/{review_id}/file-content")
async def get_cv_file_content(
    review_id: UUID, session: AsyncSession = Depends(get_db_session)
):
    review = await session.get(CVReview, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="CV review not found")
    try:
        data, content_type = await run_in_threadpool(
            download_cv, review.cv_object_key
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Unable to access CV in MinIO"
        ) from exc
    return Response(
        content=data,
        media_type=content_type or "application/octet-stream",
        headers={"Content-Disposition": "inline"},
    )


@router.get("/{review_id}", response_model=CVReviewResponse)
async def get_cv_review(
    review_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    review = await session.get(CVReview, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="CV review not found")
    return review


@router.patch("/{review_id}", response_model=CVReviewResponse)
async def update_cv_review(
    review_id: UUID,
    data: CVReviewUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    review = await session.get(CVReview, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="CV review not found")

    review.status = data.status
    review.approved = status_to_approved(data.status)
    review.rejection_reason = data.rejection_reason
    await session.commit()
    await session.refresh(review)
    return review
