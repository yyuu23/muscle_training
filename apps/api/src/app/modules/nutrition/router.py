"""
Nutrition API router (plan §6.3)

GET /meal-logs and PATCH /meal-logs/{id}; creation via sync events.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, ErrorCode
from app.db.models.nutrition import MealLog
from app.db.session import get_db_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.nutrition.schemas import (
    MealLogListResponse,
    MealLogPatchRequest,
    MealLogResponse,
)

router = APIRouter()


@router.get("/meal-logs", response_model=MealLogListResponse)
async def list_meal_logs(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(30, ge=1, le=100),
    cursor: str | None = Query(None),
):
    query = (
        select(MealLog)
        .where(MealLog.user_id == user.id)
        .order_by(MealLog.occurred_at.desc())
        .limit(limit + 1)
    )
    if cursor:
        query = query.where(MealLog.occurred_at < datetime.fromisoformat(cursor))

    result = await db.execute(query)
    rows = list(result.scalars().all())

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = rows[-1].occurred_at.isoformat()

    return MealLogListResponse(
        items=[MealLogResponse.model_validate(m) for m in rows],
        next_cursor=next_cursor,
    )


@router.patch("/meal-logs/{meal_id}", response_model=MealLogResponse)
async def patch_meal_log(
    meal_id: UUID,
    request_data: MealLogPatchRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Online correction with optimistic locking."""
    meal = await db.get(MealLog, meal_id)
    if meal is None or meal.user_id != user.id:
        raise ApiError(ErrorCode.NOT_FOUND, "记录不存在")

    if meal.version != request_data.expected_version:
        raise ApiError(ErrorCode.VERSION_CONFLICT, "记录已被修改，请刷新后重试")

    changed = False
    for field in ("description", "meal_type", "nutrition", "nutrition_source"):
        value = getattr(request_data, field)
        if value is not None and getattr(meal, field) != value:
            setattr(meal, field, value)
            changed = True

    if changed:
        meal.version += 1
        await db.commit()
        await db.refresh(meal)

    return MealLogResponse.model_validate(meal)
