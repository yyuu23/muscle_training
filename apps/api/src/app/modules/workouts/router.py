"""
Workout session management API router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.workouts.schemas import (
    CompleteSessionRequest,
    SessionExerciseCreateRequest,
    SessionExerciseResponse,
    WorkoutSessionCreateRequest,
    WorkoutSessionResponse,
    WorkoutSetCreateRequest,
    WorkoutSetResponse,
)
from app.modules.workouts.service import WorkoutService

router = APIRouter()


@router.post("/sessions", response_model=WorkoutSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request_data: WorkoutSessionCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Create new workout session"""
    service = WorkoutService(db)
    session = await service.create_session(user.id, request_data)
    return WorkoutSessionResponse.model_validate(session)


@router.get("/sessions/{session_id}", response_model=WorkoutSessionResponse)
async def get_session(
    session_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Get workout session"""
    service = WorkoutService(db)
    session = await service.get_session(session_id, user.id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return WorkoutSessionResponse.model_validate(session)


@router.post("/sessions/{session_id}/complete", response_model=WorkoutSessionResponse)
async def complete_session(
    session_id: str,
    request_data: CompleteSessionRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Complete workout session"""
    service = WorkoutService(db)

    try:
        session = await service.complete_session(session_id, user.id, request_data)
        return WorkoutSessionResponse.model_validate(session)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/sessions/{session_id}/exercises", response_model=SessionExerciseResponse, status_code=status.HTTP_201_CREATED)
async def add_exercise_to_session(
    session_id: str,
    request_data: SessionExerciseCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Add exercise to session"""
    service = WorkoutService(db)

    try:
        exercise = await service.add_exercise(session_id, user.id, request_data)
        return SessionExerciseResponse.model_validate(exercise)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/sessions/{session_id}/exercises", response_model=list[SessionExerciseResponse])
async def get_session_exercises(
    session_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Get exercises for session"""
    service = WorkoutService(db)

    try:
        exercises = await service.get_session_exercises(session_id, user.id)
        return [SessionExerciseResponse.model_validate(ex) for ex in exercises]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/exercises/{exercise_id}/sets", response_model=WorkoutSetResponse, status_code=status.HTTP_201_CREATED)
async def record_set(
    exercise_id: str,
    request_data: WorkoutSetCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Record workout set"""
    service = WorkoutService(db)

    try:
        workout_set = await service.record_set(exercise_id, user.id, request_data)
        return WorkoutSetResponse.model_validate(workout_set)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/exercises/{exercise_id}/sets", response_model=list[WorkoutSetResponse])
async def get_exercise_sets(
    exercise_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Get sets for exercise"""
    service = WorkoutService(db)

    try:
        sets = await service.get_exercise_sets(exercise_id, user.id)
        return [WorkoutSetResponse.model_validate(s) for s in sets]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
