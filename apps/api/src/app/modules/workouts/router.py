"""
Workout API router (plan §6.3)

Read + online correction endpoints. New records arrive exclusively via
POST /sync/events (single write path, plan §6.3 note).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, ErrorCode
from app.db.session import get_db_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.workouts.schemas import (
    SessionDetailResponse,
    SessionExerciseResponse,
    WorkoutSessionListResponse,
    WorkoutSessionPatchRequest,
    WorkoutSessionResponse,
    WorkoutSetPatchRequest,
    WorkoutSetResponse,
)
from app.modules.workouts.service import WorkoutService

router = APIRouter()


@router.get("/sessions", response_model=WorkoutSessionListResponse)
async def list_sessions(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(30, ge=1, le=100),
    cursor: str | None = Query(None),
    active_only: bool = Query(False),
):
    """Training history (newest first, cursor pagination)."""
    service = WorkoutService(db)
    sessions, next_cursor = await service.list_sessions(
        user.id, limit=limit, cursor=cursor, include_completed=not active_only
    )
    return WorkoutSessionListResponse(
        items=[WorkoutSessionResponse.model_validate(s) for s in sessions],
        next_cursor=next_cursor,
    )


@router.get("/sessions/active", response_model=WorkoutSessionResponse | None)
async def get_active_session(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Current unfinished session, even if started earlier."""
    service = WorkoutService(db)
    session = await service.get_active_session(user.id)
    return session


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Session with exercises and recorded sets."""
    service = WorkoutService(db)
    session = await service.get_session(session_id, user.id)
    if session is None:
        raise ApiError(ErrorCode.NOT_FOUND, "训练不存在")

    exercises = await service.list_session_exercises(session_id, user.id)
    sets = await service.list_session_sets(session_id, user.id)

    return SessionDetailResponse(
        session=WorkoutSessionResponse.model_validate(session),
        exercises=[SessionExerciseResponse.model_validate(e) for e in exercises],
        sets=[WorkoutSetResponse.model_validate(s) for s in sets],
    )


@router.patch("/sessions/{session_id}", response_model=WorkoutSessionResponse)
async def patch_session(
    session_id: UUID,
    request_data: WorkoutSessionPatchRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Online correction of session metadata."""
    service = WorkoutService(db)
    session = await service.patch_session(
        session_id,
        user.id,
        expected_version=request_data.expected_version,
        notes=request_data.notes,
        status=request_data.status,
        reason=request_data.reason,
    )
    return WorkoutSessionResponse.model_validate(session)


@router.get("/sessions/{session_id}/exercises", response_model=list[SessionExerciseResponse])
async def get_session_exercises(
    session_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    service = WorkoutService(db)
    exercises = await service.list_session_exercises(session_id, user.id)
    return [SessionExerciseResponse.model_validate(e) for e in exercises]


@router.patch("/sets/{set_id}", response_model=WorkoutSetResponse)
async def patch_set(
    set_id: UUID,
    request_data: WorkoutSetPatchRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Online correction of a recorded set (version + reason required)."""
    service = WorkoutService(db)
    s = await service.patch_set(
        set_id,
        user.id,
        expected_version=request_data.expected_version,
        load_kg=request_data.load_kg,
        load_mode=request_data.load_mode,
        reps=request_data.reps,
        duration_seconds=request_data.duration_seconds,
        rir=request_data.rir,
        status=request_data.status,
        reason=request_data.reason,
    )
    return WorkoutSetResponse.model_validate(s)


@router.delete("/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_set(
    set_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
    expected_version: int = Query(..., ge=1),
):
    """Online deletion of a recorded set."""
    service = WorkoutService(db)
    await service.delete_set(set_id, user.id, expected_version=expected_version)
    return None
