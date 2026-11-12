"""
Measurement API router (plan §6.3)

Read-only list; new measurements arrive via sync events (single write path).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.nutrition import Measurement
from app.db.session import get_db_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.measurements.schemas import MeasurementListResponse, MeasurementResponse

router = APIRouter()


@router.get("", response_model=MeasurementListResponse)
async def list_measurements(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
    measurement_type: str | None = Query(None),
    limit: int = Query(30, ge=1, le=100),
    cursor: str | None = Query(None),
):
    """Body observation list (weight first-class; others type-system only)."""
    from datetime import datetime

    query = (
        select(Measurement)
        .where(Measurement.user_id == user.id)
        .order_by(Measurement.observed_at.desc())
        .limit(limit + 1)
    )
    if measurement_type:
        query = query.where(Measurement.measurement_type == measurement_type)
    if cursor:
        query = query.where(Measurement.observed_at < datetime.fromisoformat(cursor))

    result = await db.execute(query)
    rows = list(result.scalars().all())

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = rows[-1].observed_at.isoformat()

    return MeasurementListResponse(
        items=[MeasurementResponse.model_validate(m) for m in rows],
        next_cursor=next_cursor,
    )
