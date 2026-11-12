"""
Weekly review job handler (plan §7.12)

Scheduled Mondays 04:00 per user timezone. Statistics by code; model
interprets. Insufficient data → fixed result, no model call.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.queue import complete_job, fail_job
from app.modules.reviews.builder import week_start_for
from app.modules.reviews.service import ReviewService

logger = logging.getLogger(__name__)


async def handle_weekly_review(db: AsyncSession, job) -> None:
    user_id = UUID(job.payload["user_id"])
    week_start_str = job.payload.get("week_start")

    from datetime import datetime

    week_start = datetime.fromisoformat(week_start_str) if week_start_str else week_start_for(datetime.now(tz=None))

    try:
        service = ReviewService(db)
        review = await service.get_or_create_review(user_id, week_start=week_start)
        await complete_job(db, job.id, {"review_id": str(review.id)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("weekly review failed")
        await fail_job(db, job.id, error_code="REVIEW_ERROR", error_detail=str(exc)[:500])
