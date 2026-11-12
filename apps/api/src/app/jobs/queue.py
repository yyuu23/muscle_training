"""
Job queue backed by PostgreSQL (plan §9.1)

- FOR UPDATE SKIP LOCKED claiming; lease committed immediately.
- Default lease 60s, renewed every 20s by the worker.
- External waits reschedule via run_after (waiting_external).
- dedupe_key prevents double-submission and scheduler duplicates.
"""

import socket
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, ErrorCode
from app.config import get_settings
from app.db.models.operations import Job

WORKER_ID = f"{socket.gethostname()}:{id(Job)}"


async def enqueue_job(
    db: AsyncSession,
    *,
    job_type: str,
    owner_user_id: UUID | None,
    payload: dict,
    dedupe_key: str | None = None,
    run_after: datetime | None = None,
) -> Job:
    """Create a job; a live dedupe_key returns the existing job."""
    if dedupe_key:
        existing = (
            await db.execute(
                select(Job)
                .where(Job.dedupe_key == dedupe_key)
                .where(Job.status.in_(("queued", "running", "waiting_external")))
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

    job = Job(
        id=uuid4(),
        owner_user_id=owner_user_id,
        type=job_type,
        status="queued",
        payload=payload,
        dedupe_key=dedupe_key,
        run_after=run_after or datetime.now(tz=None),
        max_attempts=get_settings().worker_max_attempts,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def claim_jobs(
    db: AsyncSession,
    *,
    limit: int = 1,
    types: list[str] | None = None,
) -> list[Job]:
    """Claim runnable jobs with FOR UPDATE SKIP LOCKED."""
    now = datetime.now(tz=None)

    query = (
        select(Job)
        .where(Job.status == "queued")
        .where(Job.run_after <= now)
        .order_by(Job.run_after)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    if types:
        query = query.where(Job.type.in_(types))

    result = await db.execute(query)
    jobs = list(result.scalars().all())
    if not jobs:
        return []

    for job in jobs:
        job.status = "running"
        job.lease_owner = WORKER_ID
        job.lease_expires_at = now + timedelta(seconds=get_settings().worker_lease_timeout_seconds)
        job.attempts += 1
        job.started_at = job.started_at or now

    # Commit the lease immediately (plan §9.1)
    await db.commit()
    for job in jobs:
        await db.refresh(job)
    return jobs


async def reclaim_expired_jobs(db: AsyncSession) -> int:
    """Requeue jobs whose lease expired (worker crash recovery)."""
    now = datetime.now(tz=None)
    result = await db.execute(
        update(Job)
        .where(Job.status == "running")
        .where(Job.lease_expires_at < now)
        .where(Job.attempts < Job.max_attempts)
        .values(status="queued", lease_owner=None, lease_expires_at=None)
    )
    expired_hard = await db.execute(
        update(Job)
        .where(Job.status == "running")
        .where(Job.lease_expires_at < now)
        .where(Job.attempts >= Job.max_attempts)
        .values(status="needs_attention", error_code="LEASE_EXPIRED")
    )
    await db.commit()
    return (result.rowcount or 0) + (expired_hard.rowcount or 0)


async def renew_lease(db: AsyncSession, job_id: UUID) -> None:
    """Extend the lease of a running job."""
    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .where(Job.status == "running")
        .values(lease_expires_at=datetime.now(tz=None) + timedelta(seconds=get_settings().worker_lease_timeout_seconds))
    )
    await db.commit()


async def complete_job(db: AsyncSession, job_id: UUID, result_ref: dict | None = None) -> None:
    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(
            status="succeeded",
            result_ref=result_ref,
            completed_at=datetime.now(tz=None),
            lease_owner=None,
            lease_expires_at=None,
        )
    )
    await db.commit()


async def fail_job(
    db: AsyncSession,
    job_id: UUID,
    *,
    error_code: str,
    error_detail: str | None = None,
    retryable: bool = True,
) -> None:
    """Fail a job: retry up to max_attempts, else needs_attention."""
    job = await db.get(Job, job_id)
    if job is None:
        return

    job.error_code = error_code[:100]
    job.error_detail = (error_detail or "")[:2000]

    if retryable and job.attempts < job.max_attempts:
        job.status = "queued"
        job.run_after = datetime.now(tz=None) + timedelta(seconds=30)
        job.lease_owner = None
        job.lease_expires_at = None
    else:
        job.status = "needs_attention"
        job.lease_owner = None
        job.lease_expires_at = None

    await db.commit()


async def defer_job(
    db: AsyncSession,
    job_id: UUID,
    *,
    run_after: datetime,
    external_task_id: str | None = None,
    phase: str | None = None,
) -> None:
    """Reschedule as waiting_external (no DB transaction held during waits)."""
    job = await db.get(Job, job_id)
    if job is None:
        return
    job.status = "waiting_external"
    job.run_after = run_after
    job.lease_owner = None
    job.lease_expires_at = None
    if external_task_id is not None:
        job.external_task_id = external_task_id
    if phase is not None:
        job.phase = phase
    await db.commit()


async def resume_waiting_jobs(db: AsyncSession, *, types: list[str] | None = None) -> list[Job]:
    """Move waiting_external jobs whose run_after passed back to queued."""
    now = datetime.now(tz=None)
    query = (
        select(Job)
        .where(Job.status == "waiting_external")
        .where(Job.run_after <= now)
        .with_for_update(skip_locked=True)
    )
    if types:
        query = query.where(Job.type.in_(types))

    result = await db.execute(query)
    jobs = list(result.scalars().all())
    for job in jobs:
        job.status = "queued"
        job.attempts -= 1  # external waits don't consume attempts
    await db.commit()
    return jobs


async def poll_external_jobs(db: AsyncSession, *, types: list[str] | None = None) -> list[Job]:
    """Jobs with external_task_id in waiting_external ready for polling."""
    now = datetime.now(tz=None)
    query = (
        select(Job)
        .where(Job.status == "waiting_external")
        .where(Job.run_after <= now)
        .where(Job.external_task_id.isnot(None))
        .with_for_update(skip_locked=True)
    )
    if types:
        query = query.where(Job.type.in_(types))
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_job(db: AsyncSession, job_id: UUID, user_id: UUID | None = None) -> Job | None:
    """Load a job; owner check for non-admin access."""
    job = await db.get(Job, job_id)
    if job is None:
        return None
    if user_id is not None and job.owner_user_id != user_id:
        return None
    return job


async def count_running_jobs(db: AsyncSession, job_type: str, owner_user_id: UUID | None = None) -> int:
    """Count live jobs of a type (per-user high-cost job limits, plan §9.1)."""
    from sqlalchemy import func

    query = (
        select(func.count())
        .select_from(Job)
        .where(Job.type == job_type)
        .where(Job.status.in_(("queued", "running", "waiting_external")))
    )
    if owner_user_id is not None:
        query = query.where(Job.owner_user_id == owner_user_id)
    return (await db.execute(query)).scalar() or 0


async def jobs_healthcheck(db: AsyncSession) -> bool:
    try:
        await db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


__all__ = [
    "ApiError",
    "ErrorCode",
    "WORKER_ID",
    "enqueue_job",
    "claim_jobs",
    "reclaim_expired_jobs",
    "renew_lease",
    "complete_job",
    "fail_job",
    "defer_job",
    "resume_waiting_jobs",
    "poll_external_jobs",
    "get_job",
    "count_running_jobs",
    "jobs_healthcheck",
]
