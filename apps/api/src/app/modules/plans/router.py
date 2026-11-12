"""
Plan API router (plan §6.3)

Plan generation runs as a background job (202 + job_id).
Activation is an explicit user action; never automatic.
"""

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.plans.schemas import (
    PlanActivateRequest,
    PlanActivateResponse,
    PlanActiveResponse,
    PlanDetailResponse,
    PlanListResponse,
    PlanVersionResponse,
)
from app.modules.plans.service import PlanService

router = APIRouter()


@router.get("/active", response_model=PlanActiveResponse)
async def get_active_plan(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Current active plan; plan:null when none exists."""
    service = PlanService(db)
    plan = await service.get_active_plan(user.id)
    return PlanActiveResponse(
        plan=PlanVersionResponse.model_validate(plan) if plan else None
    )


@router.get("", response_model=PlanListResponse)
async def list_plans(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(30, ge=1, le=100),
    cursor: str | None = Query(None),
):
    """Plan version history."""
    service = PlanService(db)
    plans, next_cursor = await service.list_plans(user.id, limit=limit, cursor=cursor)
    return PlanListResponse(
        items=[PlanVersionResponse.model_validate(p) for p in plans],
        next_cursor=next_cursor,
    )


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_plan(
    user: CurrentUser,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a plan generation job; returns 202 with job_id."""
    from app.api.errors import ApiError
    from app.jobs.queue import enqueue_job

    try:
        job = await enqueue_job(
            db,
            job_type="plan_generate",
            owner_user_id=user.id,
            payload={"user_id": str(user.id)},
            dedupe_key=f"plan_generate:{user.id}",
        )
    except ApiError as exc:
        raise exc

    return {"job_id": str(job.id), "status": job.status}


@router.get("/{plan_id}", response_model=PlanDetailResponse)
async def get_plan(
    plan_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Plan with basis, validation results and diff vs active."""
    from app.api.errors import ApiError, ErrorCode

    service = PlanService(db)
    plan = await service.get_plan(plan_id, user.id)
    if plan is None:
        raise ApiError(ErrorCode.NOT_FOUND, "计划不存在")

    detail = await service.plan_detail(plan, user.id)
    return PlanDetailResponse(
        plan=PlanVersionResponse.model_validate(detail["plan"]),
        validation_issues=detail["validation_issues"],
        diff_vs_active=detail["diff_vs_active"],
    )


@router.post("/{plan_id}/activate", response_model=PlanActivateResponse)
async def activate_plan(
    plan_id: uuid.UUID,
    request_data: PlanActivateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Adopt a draft plan after basis validation."""
    service = PlanService(db)
    plan, superseded = await service.activate_plan(
        plan_id,
        user.id,
        expected_basis_planning_revision=request_data.expected_basis_planning_revision,
    )
    return PlanActivateResponse(
        plan=PlanVersionResponse.model_validate(plan),
        superseded_plan_id=superseded.id if superseded else None,
    )
