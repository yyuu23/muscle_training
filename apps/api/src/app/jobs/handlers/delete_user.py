"""
User deletion job handler (plan §9.5)

Covers raw data, candidates, summaries, vectors, revisions and
attachments; records the deletion ledger for restore re-application.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.queue import complete_job, fail_job
from app.modules.deletion.ledger import delete_user_data

logger = logging.getLogger(__name__)


async def handle_user_delete(db: AsyncSession, job) -> None:
    user_id = UUID(job.payload["user_id"])
    try:
        counts = await delete_user_data(db, user_id)
        await complete_job(db, job.id, {"deleted": counts})
    except Exception as exc:  # noqa: BLE001
        logger.exception("user deletion failed")
        await fail_job(db, job.id, error_code="DELETE_ERROR", error_detail=str(exc)[:500])
