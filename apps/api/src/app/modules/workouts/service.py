"""
Workout service (plan §5.5 / §6.3)

- Cross-user access surfaces as None → router maps to 404.
- Corrections record revisions and bump planning_revision.
- Skipped never fakes zero reps; unknown values stay null.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, ErrorCode
from app.db.models.training import (
    RecordRevision,
    SessionExercise,
    WorkoutSession,
    WorkoutSet,
)
from app.services.planning import bump_planning_revision


def _snapshot(obj) -> dict:
    """JSON-safe snapshot of a record for revision history."""
    data = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, UUID):
            value = str(value)
        elif value is not None and not isinstance(value, (str, int, float, bool, list, dict)):
            value = str(value)
        data[column.name] = value
    return data


class WorkoutService:
    """Workout session business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    async def create_session(
        self,
        user_id: UUID,
        *,
        session_id: UUID,
        plan_version_id: UUID | None,
        plan_day_key: str | None,
        started_at: datetime,
        precheck: dict | None,
    ) -> WorkoutSession:
        """Create a session with a client-supplied id (sync-idempotent)."""
        existing = await self.db.get(WorkoutSession, session_id)
        if existing is not None:
            if existing.user_id != user_id:
                # Same id under another user: reject, never leak
                raise ApiError(ErrorCode.IDEMPOTENCY_CONFLICT, "记录标识冲突")
            return existing

        session = WorkoutSession(
            id=session_id,
            user_id=user_id,
            plan_version_id=plan_version_id,
            plan_day_key=plan_day_key,
            started_at=started_at,
            precheck=precheck,
            status="in_progress",
            version=1,
        )
        self.db.add(session)
        await self.db.flush()
        await bump_planning_revision(self.db, user_id)
        return session

    async def get_session(self, session_id: UUID, user_id: UUID) -> WorkoutSession | None:
        session = await self.db.get(WorkoutSession, session_id)
        if session is None or session.user_id != user_id:
            return None
        return session

    async def list_sessions(
        self,
        user_id: UUID,
        *,
        limit: int = 30,
        cursor: str | None = None,
        include_completed: bool = True,
    ) -> tuple[list[WorkoutSession], str | None]:
        """Newest-first cursor pagination."""
        query = (
            select(WorkoutSession)
            .where(WorkoutSession.user_id == user_id)
            .order_by(WorkoutSession.started_at.desc())
            .limit(limit + 1)
        )
        if not include_completed:
            query = query.where(WorkoutSession.status == "in_progress")
        if cursor:
            query = query.where(WorkoutSession.started_at < datetime.fromisoformat(cursor))

        result = await self.db.execute(query)
        rows = list(result.scalars().all())

        next_cursor = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = rows[-1].started_at.isoformat()
        return rows, next_cursor

    async def get_active_session(self, user_id: UUID) -> WorkoutSession | None:
        """Most recent in-progress session, even if started earlier (plan §8.6)."""
        result = await self.db.execute(
            select(WorkoutSession)
            .where(WorkoutSession.user_id == user_id)
            .where(WorkoutSession.status == "in_progress")
            .order_by(WorkoutSession.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def complete_session(
        self,
        session_id: UUID,
        user_id: UUID,
        *,
        completed_at: datetime,
        notes: str | None,
    ) -> WorkoutSession:
        """Complete a session (idempotent via sync layer)."""
        session = await self.get_session(session_id, user_id)
        if session is None:
            raise ApiError(ErrorCode.NOT_FOUND, "训练不存在")

        if session.status == "completed":
            return session

        if completed_at < session.started_at:
            raise ApiError(ErrorCode.VALIDATION_ERROR, "完成时间不能早于开始时间")

        session.completed_at = completed_at
        session.status = "completed"
        session.version += 1
        if notes is not None:
            session.notes = notes
        await self.db.flush()
        await bump_planning_revision(self.db, user_id)
        return session

    async def patch_session(
        self,
        session_id: UUID,
        user_id: UUID,
        *,
        expected_version: int,
        notes: str | None,
        status: str | None,
        reason: str,
    ) -> WorkoutSession:
        """Online correction of session metadata with optimistic locking."""
        session = await self.get_session(session_id, user_id)
        if session is None:
            raise ApiError(ErrorCode.NOT_FOUND, "训练不存在")

        if session.version != expected_version:
            raise ApiError(ErrorCode.VERSION_CONFLICT, "记录已被修改，请刷新后重试")

        previous = _snapshot(session)
        changed: list[str] = []

        if notes is not None and notes != session.notes:
            session.notes = notes
            changed.append("notes")
        if status is not None and status != session.status:
            if session.status == "completed" and status != "completed":
                # Late logs reopen the session; old reviews must go stale
                session.completed_at = None
            session.status = status
            if status == "completed" and session.completed_at is None:
                session.completed_at = datetime.now(tz=None)
            changed.append("status")

        if not changed:
            return session

        session.version += 1
        self.db.add(
            RecordRevision(
                user_id=user_id,
                entity_type="workout_session",
                entity_id=session.id,
                previous_version=expected_version,
                previous_value=previous,
                changed_fields=changed,
                reason=reason,
            )
        )
        await self.db.flush()
        await bump_planning_revision(self.db, user_id)
        await self._mark_reviews_stale(user_id)
        return session

    # ------------------------------------------------------------------
    # Session exercises
    # ------------------------------------------------------------------

    async def add_exercise(
        self,
        user_id: UUID,
        session_id: UUID,
        *,
        session_exercise_id: UUID,
        exercise_id: UUID,
        plan_item_id: str | None,
        position: int,
        equipment_label: str | None,
        override_reason: str | None,
    ) -> SessionExercise:
        """Add an exercise to a session (temporary substitution binds to this session only)."""
        session = await self.get_session(session_id, user_id)
        if session is None:
            raise ApiError(ErrorCode.NOT_FOUND, "训练不存在")

        existing = await self.db.get(SessionExercise, session_exercise_id)
        if existing is not None:
            if existing.user_id != user_id:
                raise ApiError(ErrorCode.IDEMPOTENCY_CONFLICT, "记录标识冲突")
            return existing

        exercise = SessionExercise(
            id=session_exercise_id,
            user_id=user_id,
            session_id=session_id,
            exercise_id=exercise_id,
            plan_item_id=plan_item_id,
            position=position,
            equipment_label=equipment_label,
            override_reason=override_reason,
            completion_status="not_recorded",
            version=1,
        )
        self.db.add(exercise)
        await self.db.flush()
        return exercise

    async def get_session_exercise(
        self, session_exercise_id: UUID, user_id: UUID
    ) -> SessionExercise | None:
        ex = await self.db.get(SessionExercise, session_exercise_id)
        if ex is None or ex.user_id != user_id:
            return None
        return ex

    async def list_session_exercises(self, session_id: UUID, user_id: UUID) -> list[SessionExercise]:
        result = await self.db.execute(
            select(SessionExercise)
            .where(SessionExercise.session_id == session_id)
            .where(SessionExercise.user_id == user_id)
            .order_by(SessionExercise.position)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Sets
    # ------------------------------------------------------------------

    async def log_set(
        self,
        user_id: UUID,
        *,
        set_id: UUID,
        session_exercise_id: UUID,
        set_index: int,
        set_kind: str,
        status: str,
        load_kg,
        load_mode: str | None,
        reps: int | None,
        duration_seconds: int | None,
        rir: int | None,
        discomfort_report: str | None,
        performed_at: datetime,
    ) -> WorkoutSet:
        """Record one set (idempotent by set_id via sync layer)."""
        parent = await self.get_session_exercise(session_exercise_id, user_id)
        if parent is None:
            raise ApiError(ErrorCode.DEPENDENCY_PENDING, "所属动作记录不存在")

        # set_index unique per session_exercise (plan §5.5)
        dup = await self.db.execute(
            select(WorkoutSet)
            .where(WorkoutSet.session_exercise_id == session_exercise_id)
            .where(WorkoutSet.set_index == set_index)
        )
        existing_index = dup.scalar_one_or_none()
        if existing_index is not None and existing_index.id != set_id:
            raise ApiError(
                ErrorCode.IDEMPOTENCY_CONFLICT,
                f"第 {set_index} 组已存在",
                {"existing_set_id": str(existing_index.id)},
            )

        existing = await self.db.get(WorkoutSet, set_id)
        if existing is not None:
            if existing.user_id != user_id:
                raise ApiError(ErrorCode.IDEMPOTENCY_CONFLICT, "记录标识冲突")
            return existing

        workout_set = WorkoutSet(
            id=set_id,
            user_id=user_id,
            session_exercise_id=session_exercise_id,
            set_index=set_index,
            set_kind=set_kind,
            status=status,
            load_kg=load_kg,
            load_mode=load_mode,
            reps=reps,
            duration_seconds=duration_seconds,
            rir=rir,
            discomfort_report=discomfort_report,
            performed_at=performed_at,
            version=1,
        )
        self.db.add(workout_set)
        await self.db.flush()

        # Refresh parent completion status from its sets
        await self._refresh_exercise_completion(parent)

        await bump_planning_revision(self.db, user_id)
        return workout_set

    async def get_set(self, set_id: UUID, user_id: UUID) -> WorkoutSet | None:
        s = await self.db.get(WorkoutSet, set_id)
        if s is None or s.user_id != user_id:
            return None
        return s

    async def list_session_sets(self, session_id: UUID, user_id: UUID) -> list[WorkoutSet]:
        result = await self.db.execute(
            select(WorkoutSet)
            .join(SessionExercise, WorkoutSet.session_exercise_id == SessionExercise.id)
            .where(SessionExercise.session_id == session_id)
            .where(WorkoutSet.user_id == user_id)
            .order_by(WorkoutSet.performed_at)
        )
        return list(result.scalars().all())

    async def patch_set(
        self,
        set_id: UUID,
        user_id: UUID,
        *,
        expected_version: int,
        reason: str,
        load_kg=None,
        load_mode: str | None = None,
        reps: int | None = None,
        duration_seconds: int | None = None,
        rir: int | None = None,
        status: str | None = None,
    ) -> WorkoutSet:
        """Online correction of a recorded set."""
        s = await self.get_set(set_id, user_id)
        if s is None:
            raise ApiError(ErrorCode.NOT_FOUND, "记录不存在")

        if s.version != expected_version:
            raise ApiError(ErrorCode.VERSION_CONFLICT, "记录已被修改，请刷新后重试")

        previous = _snapshot(s)
        changed: list[str] = []

        for field, value in (
            ("load_kg", load_kg),
            ("load_mode", load_mode),
            ("reps", reps),
            ("duration_seconds", duration_seconds),
            ("rir", rir),
            ("status", status),
        ):
            if value is not None and getattr(s, field) != value:
                setattr(s, field, value)
                changed.append(field)

        if not changed:
            return s

        s.version += 1
        self.db.add(
            RecordRevision(
                user_id=user_id,
                entity_type="workout_set",
                entity_id=s.id,
                previous_version=expected_version,
                previous_value=previous,
                changed_fields=changed,
                reason=reason,
            )
        )
        await self.db.flush()
        await bump_planning_revision(self.db, user_id)
        await self._mark_reviews_stale(user_id)
        return s

    async def delete_set(self, set_id: UUID, user_id: UUID, *, expected_version: int) -> None:
        """Online deletion of a recorded set (version checked)."""
        s = await self.get_set(set_id, user_id)
        if s is None:
            raise ApiError(ErrorCode.NOT_FOUND, "记录不存在")

        if s.version != expected_version:
            raise ApiError(ErrorCode.VERSION_CONFLICT, "记录已被修改，请刷新后重试")

        self.db.add(
            RecordRevision(
                user_id=user_id,
                entity_type="workout_set",
                entity_id=s.id,
                previous_version=expected_version,
                previous_value=_snapshot(s),
                changed_fields=["__deleted__"],
                reason="user_delete",
            )
        )
        await self.db.execute(delete(WorkoutSet).where(WorkoutSet.id == set_id))
        await self.db.flush()
        await bump_planning_revision(self.db, user_id)
        await self._mark_reviews_stale(user_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _refresh_exercise_completion(self, exercise: SessionExercise) -> None:
        """Recompute completion status from recorded sets."""
        result = await self.db.execute(
            select(WorkoutSet).where(WorkoutSet.session_exercise_id == exercise.id)
        )
        sets = list(result.scalars().all())
        if not sets:
            exercise.completion_status = "not_recorded"
            return

        work = [s for s in sets if s.set_kind == "work"]
        if all(s.status == "skipped" for s in work):
            exercise.completion_status = "skipped"
        elif all(s.status == "completed" for s in work):
            exercise.completion_status = "completed"
        else:
            exercise.completion_status = "partial"
        exercise.version += 1

    async def _mark_reviews_stale(self, user_id: UUID) -> None:
        """Corrections/deletions mark old reviews stale (plan §7.12)."""
        from app.db.models.operations import WeeklyReview

        result = await self.db.execute(
            select(WeeklyReview)
            .where(WeeklyReview.user_id == user_id)
            .where(WeeklyReview.stale.is_(False))
        )
        for review in result.scalars().all():
            review.stale = True
