"""
Catalog public API router (plan §6.3)

GET /exercises and GET /templates (mounted at /api/v1 root).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.catalog.schemas import ExerciseResponse, TemplateResponse
from app.modules.catalog.service import CatalogService

router = APIRouter()


@router.get("/exercises", response_model=list[ExerciseResponse])
async def list_exercises(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
    search: str | None = Query(None, max_length=100),
    movement_pattern: str | None = Query(None, max_length=50),
):
    """Reviewed exercise catalog."""
    service = CatalogService(db)
    exercises = await service.list_exercises(search, movement_pattern)
    return [ExerciseResponse.model_validate(e) for e in exercises]


@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
    sessions_per_week: int | None = Query(None, ge=1, le=7),
):
    """Reviewed training templates with eligibility."""
    service = CatalogService(db)
    templates = await service.list_templates(sessions_per_week)
    return [TemplateResponse.model_validate(t) for t in templates]
