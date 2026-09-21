import uuid
from pathlib import PurePath
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.db import get_db_session
from app.models import CVReview
from app.storage import upload_cv

router = APIRouter(prefix="/api/v1/cv-reviews", tags=["cv-reviews"])


@router.post("")
async def create_cv_review(
    cv: UploadFile = File(...),
    approved: bool = Form(...),
    rejection_reason: str | None = Form(None),
    session: AsyncSession = Depends(get_db_session),
):
    content = await cv.read()
    review_id = uuid.uuid4()
    filename = PurePath(cv.filename or "cv-upload").name
    object_key = f"cvs/{review_id}/{filename}"
    try:
        await run_in_threadpool(upload_cv, object_key, content, cv.content_type)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    review = CVReview(
        id=review_id,
        cv_name=filename,
        approved=approved,
        rejection_reason=rejection_reason if not approved else None,
        cv_object_key=object_key,
    )
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review


@router.get("")
async def list_cv_reviews(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(
        select(CVReview).order_by(CVReview.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{review_id}")
async def get_cv_review(
    review_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    review = await session.get(CVReview, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="CV review not found")
    return review