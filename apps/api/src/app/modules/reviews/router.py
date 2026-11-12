"""
Reviews API router (plan §6.3)
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, ErrorCode
from app.db.session import get_db_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.reviews.schemas import (
    WeeklyReviewCreateRequest,
    WeeklyReviewListResponse,
    WeeklyReviewResponse,
)
from app.modules.reviews.service import ReviewService

router = APIRouter()


@router.post("/weekly", response_model=WeeklyReviewResponse, status_code=201)
async def create_weekly_review(
    request_data: WeeklyReviewCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Same-basis result is reused; otherwise a new review is generated."""
    service = ReviewService(db)
    review = await service.get_or_create_review(user.id, week_start=request_data.week_start)
    return WeeklyReviewResponse.model_validate(review)


@router.get("/weekly", response_model=WeeklyReviewListResponse)
async def list_weekly_reviews(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    service = ReviewService(db)
    reviews = await service.list_reviews(user.id)
    return WeeklyReviewListResponse(
        items=[WeeklyReviewResponse.model_validate(r) for r in reviews]
    )


@router.get("/weekly/{review_id}", response_model=WeeklyReviewResponse)
async def get_weekly_review(
    review_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    service = ReviewService(db)
    review = await service.get_review(review_id, user.id)
    if review is None:
        raise ApiError(ErrorCode.NOT_FOUND, "复盘不存在")
    return WeeklyReviewResponse.model_validate(review)


@router.post("/weekly/{review_id}/regenerate", response_model=WeeklyReviewResponse)
async def regenerate_weekly_review(
    review_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Regenerate a stale review with current data."""
    service = ReviewService(db)
    review = await service.regenerate(review_id, user.id)
    return WeeklyReviewResponse.model_validate(review)
