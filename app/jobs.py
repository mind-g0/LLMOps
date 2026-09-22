from uuid import UUID
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.models import JobRequirement
from app.schemas import (
    JobRequirementCreate,
    JobRequirementResponse,
    JobRequirementSpec,
    JobRequirementUpdate,
)

router = APIRouter(prefix="/api/v1/job-requirements", tags=["job-requirements"])


def _ingest_to_qdrant(job_id: str) -> None:
    """Non-blocking fire-and-forget: sync the job into the agent's Qdrant store."""
    import logging
    try:
        sync_script = Path(__file__).resolve().parent.parent / "agent" / "rag" / "sync_job.py"
        if not sync_script.exists():
            logging.warning(f"[ingest] sync_job.py not found at {sync_script}")
            return
        subprocess.Popen(
            [sys.executable, str(sync_script), job_id],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        logging.error(f"[ingest] failed to trigger Qdrant sync for job {job_id}: {e}")


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
    _ingest_to_qdrant(str(job.id))
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


@router.get("/{job_id}/spec", response_model=JobRequirementSpec)
async def get_job_requirement_spec(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    job = await session.get(JobRequirement, job_id)
    if job is None or not job.active:
        raise HTTPException(status_code=404, detail="Job requirement not found")
    return JobRequirementSpec.from_orm_job(job)


@router.post("/{job_id}/ingest", status_code=202)
async def ingest_job_requirement(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    job = await session.get(JobRequirement, job_id)
    if job is None or not job.active:
        raise HTTPException(status_code=404, detail="Job requirement not found")
    _ingest_to_qdrant(str(job_id))
    return {"detail": f"Ingest triggered for job {job_id}"}


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
    _ingest_to_qdrant(str(job.id))
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