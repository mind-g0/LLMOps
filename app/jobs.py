from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.models import JobRequirement
from app.schemas import (
    JobRequirementCreate,
    JobRequirementResponse,
    JobRequirementUpdate,
)

router = APIRouter(prefix="/api/v1/job-requirements", tags=["job-requirements"])


@router.get("", response_model=list[JobRequirementResponse])
async def list_job_requirements(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(
        select(JobRequirement)
        .where(JobRequirement.active.is_(True))
        .order_by(JobRequirement.created_at.asc())
    )
    return result.scalars().all()


@router.post("", response_model=JobRequirementResponse, status_code=201)
async def create_job_requirement(
    data: JobRequirementCreate,
    session: AsyncSession = Depends(get_db_session),
):
    job = JobRequirement(**data.model_dump())
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


@router.get("/{job_id}", response_model=JobRequirementResponse)
async def get_job_requirement(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    job = await session.get(JobRequirement, job_id)
    if job is None or not job.active:
        raise HTTPException(status_code=404, detail="Job requirement not found")
    return job


@router.patch("/{job_id}", response_model=JobRequirementResponse)
async def update_job_requirement(
    job_id: UUID,
    data: JobRequirementUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    job = await session.get(JobRequirement, job_id)
    if job is None or not job.active:
        raise HTTPException(status_code=404, detail="Job requirement not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    await session.commit()
    await session.refresh(job)
    return job


@router.delete("/{job_id}", status_code=204)
async def delete_job_requirement(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    job = await session.get(JobRequirement, job_id)
    if job is None or not job.active:
        raise HTTPException(status_code=404, detail="Job requirement not found")
    job.active = False
    await session.commit()