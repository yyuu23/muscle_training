"""
Job scheduler (plan §7.12 / §9.1)

Enqueues periodic jobs at fixed times using the system timezone:
- weekly reviews: Monday 04:00 per user
- maintenance: daily 03:30

Scheduler only creates jobs; execution happens in the worker.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from app.config import get_settings
from app.db.models.auth import User
from app.db.session import async_session_maker
from app.jobs.queue import enqueue_job

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("scheduler")


def _next_run(now: datetime, *, weekday: int, hour: int, minute: int) -> datetime:
    """Next occurrence of a weekly (weekday: 0=Mon) or daily time."""
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    while candidate.weekday() != weekday:
        candidate += timedelta(days=1)
    return candidate


async def enqueue_weekly_reviews() -> int:
    """Monday 04:00: one weekly_review job per active user (last week)."""
    count = 0
    async with async_session_maker() as db:
        users = (
            await db.execute(select(User.id).where(User.status == "active"))
        ).fetchall()
        week_start = (datetime.now(tz=None) - timedelta(days=7)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        # Normalize to Monday
        week_start -= timedelta(days=week_start.weekday())

        for (user_id,) in users:
            await enqueue_job(
                db,
                job_type="weekly_review",
                owner_user_id=user_id,
                payload={"user_id": str(user_id), "week_start": week_start.isoformat()},
                dedupe_key=f"weekly_review:{user_id}:{week_start.date().isoformat()}",
            )
            count += 1
    return count


async def enqueue_maintenance() -> str:
    async with async_session_maker() as db:
        job = await enqueue_job(
            db,
            job_type="temporary_asset_cleanup",
            owner_user_id=None,
            payload={},
            dedupe_key=f"maintenance:{datetime.now(tz=None).date().isoformat()}",
        )
        return str(job.id)


async def run_forever() -> None:
    """Simple daily/weekly scheduling loop."""
    settings = get_settings()
    last_maintenance_date: str | None = None
    last_review_date: str | None = None

    logger.info("scheduler started (reviews Mon %02d:00, maintenance 03:30)", 4)
    while True:
        now = datetime.now(tz=None)

        if now.weekday() == 0 and now.hour >= 4 and last_review_date != now.date().isoformat():
            try:
                created = await enqueue_weekly_reviews()
                last_review_date = now.date().isoformat()
                logger.info("enqueued %d weekly reviews", created)
            except Exception:  # noqa: BLE001
                logger.exception("weekly review scheduling failed")

        if now.hour >= 3 and now.minute >= 30 and last_maintenance_date != now.date().isoformat():
            try:
                await enqueue_maintenance()
                last_maintenance_date = now.date().isoformat()
                logger.info("enqueued maintenance")
            except Exception:  # noqa: BLE001
                logger.exception("maintenance scheduling failed")

        await asyncio.sleep(settings.worker_poll_interval_seconds * 4)


if __name__ == "__main__":
    asyncio.run(run_forever())
