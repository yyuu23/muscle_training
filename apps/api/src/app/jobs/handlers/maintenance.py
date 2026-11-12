"""
Maintenance handler (plan §9.1 / §9.5)

- Temporary media cleanup (expired temporary_import assets).
- Sync event ledger trim (applied events older than 30 days).
- Chat retention sweep (plain conversation text > 90 days).
- Lease-expired job recovery.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.knowledge import Asset
from app.db.models.operations import Message, SyncEvent
from app.jobs.queue import complete_job, reclaim_expired_jobs
from app.storage import get_storage

logger = logging.getLogger(__name__)


async def handle_maintenance(db: AsyncSession, job) -> None:
    settings = get_settings()
    now = datetime.now(tz=None)
    results = {}

    # 1. Expired temporary media
    expired = (
        await db.execute(
            select(Asset).where(
                Asset.retention_class == "temporary_import",
                Asset.expires_at < now,
            )
        )
    ).scalars().all()
    storage = get_storage()
    deleted_assets = 0
    for asset in expired:
        try:
            await storage.delete(asset.object_key)
        except FileNotFoundError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.warning("temp asset delete failed %s: %s", asset.object_key, exc)
        asset.status = "expired"
        deleted_assets += 1
    results["expired_assets"] = deleted_assets

    # 2. Trim old sync events (keep 30 days for replay diagnostics)
    trimmed = await db.execute(
        delete(SyncEvent).where(SyncEvent.applied_at < now - timedelta(days=30))
    )
    results["trimmed_sync_events"] = trimmed.rowcount or 0

    # 3. Chat retention sweep (plan §9.5: 90 days)
    swept = await db.execute(
        delete(Message).where(Message.created_at < now - timedelta(days=settings.chat_retention_days))
    )
    results["swept_messages"] = swept.rowcount or 0

    # 4. Recover lease-expired jobs
    results["reclaimed_jobs"] = await reclaim_expired_jobs(db)

    await db.commit()
    await complete_job(db, job.id, results)
