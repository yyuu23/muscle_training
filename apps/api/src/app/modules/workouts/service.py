"""
Workout session management service
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.training import SessionExercise, WorkoutSession, WorkoutSet
from app.modules.workouts.schemas import (
    CompleteSessionRequest,
    SessionExerciseCreateRequest,
    WorkoutSessionCreateRequest,
    WorkoutSetCreateRequest,
)


class WorkoutService:
    """Workout management business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, user_id: UUID, request: WorkoutSessionCreateRequest) -> WorkoutSession:
        """Create new workout session"""
        session = WorkoutSession(
            user_id=user_id,
            plan_version_id=request.plan_version_id,
            plan_day_key=request.plan_day_key,
            started_at=request.started_at,
            status="in_progress",
            precheck=request.precheck,
            version=1,
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        return session

    async def get_session(self, session_id: UUID, user_id: UUID) -> WorkoutSession | None:
        """Get workout session"""
        result = await self.db.execute(
            select(WorkoutSession)
            .where(WorkoutSession.id == session_id)
            .where(WorkoutSession.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def complete_session(
        self, session_id: UUID, user_id: UUID, request: CompleteSessionRequest
    ) -> WorkoutSession:
        """Complete workout session"""
        session = await self.get_session(session_id, user_id)

        if not session:
            raise ValueError("Session not found")

        if session.status != "in_progress":
            raise ValueError("Session is not in progress")

        session.completed_at = request.completed_at
        session.status = "completed"
        session.version += 1

        await self.db.commit()
        await self.db.refresh(session)

        return session

    async def add_exercise(
        self, session_id: UUID, user_id: UUID, request: SessionExerciseCreateRequest
    ) -> SessionExercise:
        """Add exercise to session"""
        # Verify session belongs to user
        session = await self.get_session(session_id, user_id)
        if not session:
            raise ValueError("Session not found")

        exercise = SessionExercise(
            session_id=session_id,
            exercise_id=request.exercise_id,
            plan_item_id=request.plan_item_id,
            ordinal=request.ordinal,
            equipment_label=request.equipment_label,
            override_reason=request.override_reason,
            completion_status="not_started",
        )

        self.db.add(exercise)
        await self.db.commit()
        await self.db.refresh(exercise)

        return exercise

    async def get_session_exercises(self, session_id: UUID, user_id: UUID) -> list[SessionExercise]:
        """Get exercises for session"""
        # Verify session belongs to user
        session = await self.get_session(session_id, user_id)
        if not session:
            raise ValueError("Session not found")

        result = await self.db.execute(
            select(SessionExercise)
            .where(SessionExercise.session_id == session_id)
            .order_by(SessionExercise.ordinal)
        )
        return list(result.scalars().all())

    async def record_set(
        self, session_exercise_id: UUID, user_id: UUID, request: WorkoutSetCreateRequest
    ) -> WorkoutSet:
        """Record workout set"""
        # Verify exercise belongs to user's session
        result = await self.db.execute(
            select(SessionExercise)
            .join(WorkoutSession)
            .where(SessionExercise.id == session_exercise_id)
            .where(WorkoutSession.user_id == user_id)
        )
        exercise = result.scalar_one_or_none()

        if not exercise:
            raise ValueError("Exercise not found")

        workout_set = WorkoutSet(
            session_exercise_id=session_exercise_id,
            set_index=request.set_index,
            set_kind=request.set_kind,
            status=request.status,
            load_kg=request.load_kg,
            load_mode=request.load_mode,
            reps=request.reps,
            duration_seconds=request.duration_seconds,
            rir=request.rir,
            discomfort_report=request.discomfort_report,
            performed_at=request.performed_at,
        )

        self.db.add(workout_set)

        # Update exercise status
        if exercise.completion_status == "not_started":
            exercise.completion_status = "in_progress"

        await self.db.commit()
        await self.db.refresh(workout_set)

        return workout_set

    async def get_exercise_sets(self, session_exercise_id: UUID, user_id: UUID) -> list[WorkoutSet]:
        """Get sets for exercise"""
        # Verify exercise belongs to user's session
        result = await self.db.execute(
            select(SessionExercise)
            .join(WorkoutSession)
            .where(SessionExercise.id == session_exercise_id)
            .where(WorkoutSession.user_id == user_id)
        )
        exercise = result.scalar_one_or_none()

        if not exercise:
            raise ValueError("Exercise not found")

        result = await self.db.execute(
            select(WorkoutSet)
            .where(WorkoutSet.session_exercise_id == session_exercise_id)
            .order_by(WorkoutSet.set_index)
        )
        return list(result.scalars().all())
