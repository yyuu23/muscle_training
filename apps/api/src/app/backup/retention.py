"""
Backup retention (plan §9.5 / §9.6)

Keep the most recent 7 daily and 4 weekly backups; older ones are
deleted from the backup bucket.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, select

from app.db.models.operations import BackupRun
from app.db.session import async_session_maker
from app.storage import get_storage

logger = logging.getLogger(__name__)


def _is_weekly(snapshot_at: datetime) -> bool:
    """Weekly = the latest successful backup on/after each Monday."""
    return snapshot_at.weekday() == 0


async def apply_retention(*, daily: int = 7, weekly: int = 4) -> dict:
    """Delete backups beyond the retention windows."""
    storage = get_storage()
    async with async_session_maker() as db:
        runs = (
            await db.execute(
                select(BackupRun)
                .where(BackupRun.status == "succeeded")
                .order_by(BackupRun.snapshot_at.desc())
            )
        ).scalars().all()

    daily_keep: list[BackupRun] = []
    weekly_keep: list[BackupRun] = []
    daily_days: set[str] = set()
    weekly_weeks: set[str] = set()

    for run in runs:
        day_key = run.snapshot_at.date().isoformat()
        week_key = (run.snapshot_at.date() - timedelta(days=run.snapshot_at.weekday())).isoformat()

        if day_key not in daily_days and len(daily_days) < daily:
            daily_days.add(day_key)
            daily_keep.append(run)
        if week_key not in weekly_weeks and len(weekly_weeks) < weekly:
            weekly_weeks.add(week_key)
            weekly_keep.append(run)

    keep_ids = {run.id for run in daily_keep} | {run.id for run in weekly_keep}
    removed = 0

    async with async_session_maker() as db:
        for run in runs:
            if run.id in keep_ids:
                continue
            try:
                if run.archive_key:
                    await storage.delete(run.archive_key)
            except FileNotFoundError:
                pass
            except Exception as exc:  # noqa: BLE001
                logger.warning("retention delete failed for %s: %s", run.archive_key, exc)
                continue
            await db.execute(delete(BackupRun).where(BackupRun.id == run.id))
            removed += 1
        await db.commit()

    return {"kept": len(keep_ids), "removed": removed}
