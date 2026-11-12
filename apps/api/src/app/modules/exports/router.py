"""
Exports API router (plan §6.4)

POST /exports → 202 job; GET /exports/{id} → status + short-lived
download URL. Export files expire after 24 hours.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.jobs.queue import enqueue_job, get_job
from app.modules.auth.dependencies import CurrentUser
from app.modules.exports.schemas import ExportCreateResponse, ExportStatusResponse

router = APIRouter()


@router.post("", response_model=ExportCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_export(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Export my data as a background job."""
    job = await enqueue_job(
        db,
        job_type="user_export",
        owner_user_id=user.id,
        payload={"user_id": str(user.id)},
        dedupe_key=f"user_export:{user.id}",
    )
    return ExportCreateResponse(job_id=job.id, status=job.status)


@router.get("/{job_id}", response_model=ExportStatusResponse)
async def get_export(
    job_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Export status and short-lived download address."""
    job = await get_job(db, job_id, user_id=user.id)
    if job is None:
        from app.api.errors import ApiError, ErrorCode

        raise ApiError(ErrorCode.NOT_FOUND, "任务不存在")

    result_ref = job.result_ref or {}
    return ExportStatusResponse(
        job_id=job.id,
        status=job.status,
        download_url=result_ref.get("download_url"),
        expires_at=None if not result_ref.get("expires_at") else result_ref.get("expires_at"),
        error_code=job.error_code,
    )
