"""
Job status API (plan §6.4)

GET /jobs/{id}: the owner polls plan generation / import / export jobs.
Accessing someone else's job is a 404 (uniform private-entity rule).
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, ErrorCode
from app.db.models.operations import Job
from app.db.session import get_db_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.jobs.schemas import JobStatusResponse

router = APIRouter()


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    # System jobs (owner NULL) are infrastructure-internal: not exposed.
    if job is None or job.owner_user_id != user.id:
        raise ApiError(ErrorCode.NOT_FOUND, "任务不存在")
    return JobStatusResponse(
        job_id=str(job.id),
        status=job.status,
        phase=job.phase,
        error_code=job.error_code,
        result_ref=job.result_ref,
    )
