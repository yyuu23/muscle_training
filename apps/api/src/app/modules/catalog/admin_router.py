"""
Catalog admin API router (plan §6.4)

/admin/catalog/*: import, validate, list, review & publish. Admin only.
"""

import os
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, ErrorCode
from app.config import get_settings
from app.db.session import get_db_session
from app.modules.auth.dependencies import CurrentAdminUser
from app.modules.catalog.schemas import (
    ContentImportRequest,
    ContentImportResponse,
    ContentReviewRequest,
    ContentReviewResponse,
    ContentValidateResponse,
    ExerciseResponse,
    TemplateResponse,
)
from app.modules.catalog.service import CatalogService

router = APIRouter()

_DEFAULT_CONTENT_ROOT = os.environ.get("CONTENT_ROOT", "content")


@router.post("/import", response_model=ContentImportResponse)
async def import_content(
    request_data: ContentImportRequest,
    admin: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Import content YAML files as drafts (never auto-approved)."""
    root = request_data.content_root or _DEFAULT_CONTENT_ROOT
    service = CatalogService(db)
    imported, skipped, issues = await service.import_content(root, request_data.kind)
    return ContentImportResponse(imported=imported, skipped=skipped, issues=issues)


@router.get("/validate", response_model=ContentValidateResponse)
async def validate_content(
    admin: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
    kind: str = Query(..., pattern="^(exercises|templates)$"),
    content_root: str | None = Query(None),
):
    """Validate content files without importing."""
    service = CatalogService(db)
    issues = await service.validate_content(content_root or _DEFAULT_CONTENT_ROOT, kind)
    return ContentValidateResponse(valid=not issues, issues=issues)


@router.get("/stats")
async def content_stats(
    admin: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Content readiness summary (plan §10.3: no template → CONTENT_NOT_READY)."""
    service = CatalogService(db)
    stats = await service.content_stats()
    settings = get_settings()
    if settings.python_env == "production" and not stats["content_ready"]:
        stats["note"] = "生产环境没有已审核正式内容时，计划功能返回 CONTENT_NOT_READY"
    return stats


@router.get("/exercises", response_model=list[ExerciseResponse])
async def list_all_exercises(
    admin: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
    review_status: str | None = Query(None),
):
    service = CatalogService(db)
    exercises = await service.list_all_content("exercises", review_status)
    return [ExerciseResponse.model_validate(e) for e in exercises]


@router.get("/templates", response_model=list[TemplateResponse])
async def list_all_templates(
    admin: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
    review_status: str | None = Query(None),
):
    service = CatalogService(db)
    templates = await service.list_all_content("templates", review_status)
    return [TemplateResponse.model_validate(t) for t in templates]


@router.post("/exercises/{exercise_id}/review", response_model=ContentReviewResponse)
async def review_exercise(
    exercise_id: UUID,
    request_data: ContentReviewRequest,
    admin: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Approve or reject an exercise; writes reviewer and time."""
    service = CatalogService(db)
    exercise = await service.review_exercise(exercise_id, admin.id, request_data.decision)
    if exercise is None:
        raise ApiError(ErrorCode.NOT_FOUND, "动作不存在")
    return ContentReviewResponse(
        id=exercise.id,
        slug=exercise.slug,
        content_version=exercise.content_version,
        review_status=exercise.review_status,
        reviewed_at=exercise.reviewed_at,
    )


@router.post("/templates/{template_id}/review", response_model=ContentReviewResponse)
async def review_template(
    template_id: UUID,
    request_data: ContentReviewRequest,
    admin: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Approve or reject a template; writes reviewer and time."""
    service = CatalogService(db)
    template = await service.review_template(template_id, admin.id, request_data.decision)
    if template is None:
        raise ApiError(ErrorCode.NOT_FOUND, "模板不存在")
    return ContentReviewResponse(
        id=template.id,
        slug=template.slug,
        content_version=template.content_version,
        review_status=template.review_status,
        reviewed_at=template.reviewed_at,
    )
