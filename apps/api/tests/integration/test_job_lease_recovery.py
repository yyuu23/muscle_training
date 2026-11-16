"""
Job lease recovery (plan §9.1 / §12.2): a crashed worker's expired
lease is requeued and claimable by another worker; jobs past
max_attempts land in needs_attention instead.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import update

from app.db.models.operations import Job
from app.jobs.queue import claim_jobs, enqueue_job, reclaim_expired_jobs

pytestmark = pytest.mark.integration


async def test_expired_lease_is_requeued_and_reclaimed(db):
    job = await enqueue_job(db, job_type="weekly_review", owner_user_id=None, payload={"week": "2026-W46"})

    # Worker A claims → running with a future lease
    claimed = await claim_jobs(db, limit=1, types=["weekly_review"])
    assert [j.id for j in claimed] == [job.id]
    assert claimed[0].status == "running"
    first_attempts = claimed[0].attempts

    # Lease still valid → nothing reclaimed
    assert await reclaim_expired_jobs(db) == 0

    # Simulate worker A crashing: lease expires in the past
    await db.execute(
        update(Job)
        .where(Job.id == job.id)
        .values(lease_expires_at=datetime.now(tz=None) - timedelta(seconds=1))
    )
    await db.commit()

    assert await reclaim_expired_jobs(db) == 1

    # Worker B can claim the same job again; attempts grew
    reclaimed = await claim_jobs(db, limit=1, types=["weekly_review"])
    assert [j.id for j in reclaimed] == [job.id]
    assert reclaimed[0].status == "running"
    assert reclaimed[0].attempts == first_attempts + 1
    assert reclaimed[0].lease_owner  # new lease recorded


async def test_attempts_exhausted_goes_to_needs_attention(db):
    job = await enqueue_job(db, job_type="weekly_review", owner_user_id=None, payload={})

    # Burn all attempts via claim + expire loops
    for _ in range(job.max_attempts):
        await claim_jobs(db, limit=1, types=["weekly_review"])
        await db.execute(
            update(Job)
            .where(Job.id == job.id)
            .values(lease_expires_at=datetime.now(tz=None) - timedelta(seconds=1))
        )
        await db.commit()
        await reclaim_expired_jobs(db)

    refreshed = await db.get(Job, job.id)
    assert refreshed.status == "needs_attention"
    assert refreshed.error_code == "LEASE_EXPIRED"
    # needs_attention is terminal for claimers
    assert await claim_jobs(db, limit=1, types=["weekly_review"]) == []
