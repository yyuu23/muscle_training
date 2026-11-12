"""
Offline sync service (plan §8.4 / §8.5)

- Server deduplicates by (user_id, event_id).
- Same id + same content hash → replay first result.
- Same id + different content → IDEMPOTENCY_CONFLICT.
- Each event commits in its own transaction; one failing event never
  rolls back successful siblings.
- Parent-missing events return dependency_pending and stay retryable.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, ErrorCode
from app.db.models.catalog import Exercise, PlanVersion
from app.db.models.nutrition import MealLog, Measurement
from app.db.models.operations import SyncEvent
from app.db.models.profile import Profile, ProfileFact
from app.db.models.training import SessionExercise, WorkoutSession
from app.modules.sync.schemas import (
    MealCreatedPayload,
    MeasurementCreatedPayload,
    SessionExerciseAddedPayload,
    SetLoggedPayload,
    SyncEventItem,
    SyncEventResult,
    WorkoutCompletedPayload,
    WorkoutStartedPayload,
)
from app.services.planning import bump_planning_revision, get_user_state

logger = logging.getLogger(__name__)

PAYLOAD_MODELS = {
    "workout.started": WorkoutStartedPayload,
    "session_exercise.added": SessionExerciseAddedPayload,
    "set.logged": SetLoggedPayload,
    "workout.completed": WorkoutCompletedPayload,
    "measurement.created": MeasurementCreatedPayload,
    "meal.created": MealCreatedPayload,
}


def compute_payload_hash(payload: dict) -> str:
    """Stable hash of the event payload (sorted keys)."""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SyncService:
    """Apply offline sync events and build snapshots."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Batch application
    # ------------------------------------------------------------------

    async def apply_batch(self, user_id: UUID, events: list[SyncEventItem]) -> list[SyncEventResult]:
        results: list[SyncEventResult] = []
        for item in events:
            try:
                result = await self.apply_one(user_id, item)
            except Exception as exc:  # noqa: BLE001 - isolate event failures
                logger.exception("sync event %s failed", item.event_id)
                await self.db.rollback()
                result = SyncEventResult(
                    event_id=item.event_id,
                    outcome="rejected",
                    detail={"error": ErrorCode.VALIDATION_ERROR, "message": str(exc)[:200]},
                    retryable=False,
                )
            results.append(result)
        return results

    async def apply_one(self, user_id: UUID, item: SyncEventItem) -> SyncEventResult:
        """Apply a single event in its own transaction."""
        payload_hash = compute_payload_hash(item.payload)

        # 1. Deduplicate by (user_id, event_id)
        existing = await self._find_event(user_id, item.event_id)
        if existing is not None:
            if existing.payload_hash == payload_hash:
                # Same id + same content → replay the first result, flagged
                # as already_applied so clients can distinguish retries
                # (plan §8.5). Both outcomes count as acknowledged.
                stored = existing.result or {}
                return SyncEventResult(
                    event_id=item.event_id,
                    outcome="already_applied",
                    detail=stored.get("detail"),
                    retryable=False,
                )
            return SyncEventResult(
                event_id=item.event_id,
                outcome="rejected",
                detail={
                    "error": ErrorCode.IDEMPOTENCY_CONFLICT,
                    "message": "同一事件 ID 上传了不同内容",
                },
                retryable=False,
            )

        # 2. Validate payload shape
        model = PAYLOAD_MODELS.get(item.event_type)
        if model is None:
            return self._reject(user_id, item, payload_hash, "未知事件类型")

        try:
            payload = model.model_validate(item.payload)
        except Exception as exc:
            return self._reject(user_id, item, payload_hash, f"事件内容不合法: {exc}"[:300])

        # 3. Apply in a dedicated transaction
        try:
            detail = await self._dispatch(user_id, item.event_type, payload)
        except ApiError as exc:
            await self.db.rollback()
            if exc.code == ErrorCode.DEPENDENCY_PENDING:
                return SyncEventResult(
                    event_id=item.event_id,
                    outcome="dependency_pending",
                    detail={"message": exc.message},
                    retryable=True,
                )
            return self._reject(user_id, item, payload_hash, exc.message, exc.code)

        # 4. Persist the event ledger row with its result
        event_row = SyncEvent(
            user_id=user_id,
            event_id=item.event_id,
            device_id=item.device_id,
            event_type=item.event_type,
            payload_hash=payload_hash,
            result={"outcome": "applied", "detail": detail},
            applied_at=datetime.now(tz=None),
        )
        self.db.add(event_row)
        await self.db.commit()

        return SyncEventResult(
            event_id=item.event_id,
            outcome="applied",
            detail=detail,
        )

    async def _find_event(self, user_id: UUID, event_id: UUID) -> SyncEvent | None:
        result = await self.db.execute(
            select(SyncEvent)
            .where(SyncEvent.user_id == user_id)
            .where(SyncEvent.event_id == event_id)
        )
        return result.scalar_one_or_none()

    def _reject(
        self,
        user_id: UUID,
        item: SyncEventItem,
        payload_hash: str,
        message: str,
        error_code: str = ErrorCode.VALIDATION_ERROR,
    ) -> SyncEventResult:
        """Permanent validation errors keep a ledger row so the client
        can surface a 'needs attention' entry instead of retrying."""
        self.db.add(
            SyncEvent(
                user_id=user_id,
                event_id=item.event_id,
                device_id=item.device_id,
                event_type=item.event_type,
                payload_hash=payload_hash,
                result={"outcome": "rejected", "detail": {"error": error_code, "message": message}},
                applied_at=datetime.now(tz=None),
            )
        )
        return SyncEventResult(
            event_id=item.event_id,
            outcome="rejected",
            detail={"error": error_code, "message": message},
            retryable=False,
        )

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    async def _dispatch(self, user_id: UUID, event_type: str, payload) -> dict:
        from app.modules.workouts.service import WorkoutService

        if event_type == "workout.started":
            service = WorkoutService(self.db)
            session = await service.create_session(
                user_id,
                session_id=payload.id,
                plan_version_id=payload.plan_version_id,
                plan_day_key=payload.plan_day_key,
                started_at=payload.started_at,
                precheck=payload.precheck,
            )
            await self.db.commit()
            return {"session_id": str(session.id)}

        if event_type == "session_exercise.added":
            parent = await self.db.get(WorkoutSession, payload.session_id)
            if parent is None or parent.user_id != user_id:
                raise ApiError(ErrorCode.DEPENDENCY_PENDING, "所属训练尚未同步")

            # Exercise must exist (any review status visible to owner of record)
            exercise = await self.db.get(Exercise, payload.exercise_id)
            if exercise is None:
                raise ApiError(ErrorCode.VALIDATION_ERROR, "动作不存在")

            service = WorkoutService(self.db)
            ex = await service.add_exercise(
                user_id,
                payload.session_id,
                session_exercise_id=payload.id,
                exercise_id=payload.exercise_id,
                plan_item_id=payload.plan_item_id,
                position=payload.position,
                equipment_label=payload.equipment_label,
                override_reason=payload.override_reason,
            )
            await self.db.commit()
            return {"session_exercise_id": str(ex.id)}

        if event_type == "set.logged":
            parent = await self.db.get(SessionExercise, payload.session_exercise_id)
            if parent is None or parent.user_id != user_id:
                raise ApiError(ErrorCode.DEPENDENCY_PENDING, "所属动作记录尚未同步")

            service = WorkoutService(self.db)
            workout_set = await service.log_set(
                user_id,
                set_id=payload.id,
                session_exercise_id=payload.session_exercise_id,
                set_index=payload.set_index,
                set_kind=payload.set_kind,
                status=payload.status,
                load_kg=payload.load_kg,
                load_mode=payload.load_mode,
                reps=payload.reps,
                duration_seconds=payload.duration_seconds,
                rir=payload.rir,
                discomfort_report=payload.discomfort_report,
                performed_at=payload.performed_at,
            )
            await self.db.commit()
            return {"set_id": str(workout_set.id)}

        if event_type == "workout.completed":
            parent = await self.db.get(WorkoutSession, payload.session_id)
            if parent is None or parent.user_id != user_id:
                raise ApiError(ErrorCode.DEPENDENCY_PENDING, "所属训练尚未同步")

            service = WorkoutService(self.db)
            session = await service.complete_session(
                payload.session_id,
                user_id,
                completed_at=payload.completed_at,
                notes=payload.notes,
            )
            await self.db.commit()
            return {"session_id": str(session.id), "status": session.status}

        if event_type == "measurement.created":
            existing = await self.db.get(Measurement, payload.id)
            if existing is not None and existing.user_id == user_id:
                return {"measurement_id": str(existing.id)}
            if existing is not None:
                raise ApiError(ErrorCode.IDEMPOTENCY_CONFLICT, "记录标识冲突")

            measurement = Measurement(
                id=payload.id,
                user_id=user_id,
                measurement_type=payload.measurement_type,
                value=payload.value,
                unit=payload.unit,
                observed_at=payload.observed_at,
                source="user_logged",
                notes=payload.notes,
                version=1,
            )
            self.db.add(measurement)
            await self.db.flush()
            await bump_planning_revision(self.db, user_id)
            await self.db.commit()
            return {"measurement_id": str(measurement.id)}

        if event_type == "meal.created":
            existing = await self.db.get(MealLog, payload.id)
            if existing is not None and existing.user_id == user_id:
                return {"meal_id": str(existing.id)}
            if existing is not None:
                raise ApiError(ErrorCode.IDEMPOTENCY_CONFLICT, "记录标识冲突")

            meal = MealLog(
                id=payload.id,
                user_id=user_id,
                occurred_at=payload.occurred_at,
                meal_type=payload.meal_type,
                description=payload.description,
                items=payload.items,
                nutrition=payload.nutrition,
                nutrition_source=payload.nutrition_source,
                version=1,
            )
            self.db.add(meal)
            await self.db.commit()
            return {"meal_id": str(meal.id)}

        raise ApiError(ErrorCode.VALIDATION_ERROR, "未知事件类型")

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    async def build_snapshot(self, user_id: UUID) -> dict:
        """Snapshot for offline cache refresh (plan §8.6)."""
        from app.modules.workouts.service import WorkoutService

        state = await get_user_state(self.db, user_id)
        cutoff = datetime.now(tz=None) - timedelta(days=30)

        # Profile + active facts
        profile = (
            await self.db.execute(select(Profile).where(Profile.user_id == user_id))
        ).scalar_one_or_none()
        facts = (
            await self.db.execute(
                select(ProfileFact)
                .where(ProfileFact.user_id == user_id)
                .where(ProfileFact.superseded_by.is_(None))
            )
        ).scalars().all()

        # Active plan + exercise cards it references
        active_plan = (
            await self.db.execute(
                select(PlanVersion)
                .where(PlanVersion.user_id == user_id)
                .where(PlanVersion.status == "active")
            )
        ).scalar_one_or_none()

        exercise_query = select(Exercise).where(Exercise.review_status == "approved")
        if active_plan is not None and active_plan.content:
            referenced = {
                item.get("exercise_id")
                for day in active_plan.content.get("days", [])
                for item in day.get("exercises", [])
            }
            if referenced:
                exercise_query = exercise_query.where(Exercise.id.in_(referenced))
        exercises = (await self.db.execute(exercise_query.limit(50))).scalars().all()

        # Recent 30 days + any unfinished session even if older
        workout_service = WorkoutService(self.db)
        sessions, _ = await workout_service.list_sessions(user_id, limit=100)
        recent_sessions = [s for s in sessions if s.started_at >= cutoff or s.status == "in_progress"]

        measurements = (
            await self.db.execute(
                select(Measurement)
                .where(Measurement.user_id == user_id)
                .where(Measurement.observed_at >= cutoff)
                .order_by(Measurement.observed_at.desc())
                .limit(200)
            )
        ).scalars().all()
        meals = (
            await self.db.execute(
                select(MealLog)
                .where(MealLog.user_id == user_id)
                .where(MealLog.occurred_at >= cutoff)
                .order_by(MealLog.occurred_at.desc())
                .limit(200)
            )
        ).scalars().all()

        def _session_dict(s: WorkoutSession) -> dict:
            return {
                "id": str(s.id),
                "plan_version_id": str(s.plan_version_id) if s.plan_version_id else None,
                "plan_day_key": s.plan_day_key,
                "started_at": s.started_at.isoformat(),
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "status": s.status,
                "version": s.version,
            }

        def _measurement_dict(m: Measurement) -> dict:
            return {
                "id": str(m.id),
                "measurement_type": m.measurement_type,
                "value": str(m.value) if isinstance(m.value, Decimal) else m.value,
                "unit": m.unit,
                "observed_at": m.observed_at.isoformat(),
                "version": m.version,
            }

        def _meal_dict(x: MealLog) -> dict:
            return {
                "id": str(x.id),
                "occurred_at": x.occurred_at.isoformat(),
                "meal_type": x.meal_type,
                "description": x.description,
                "items": x.items,
                "nutrition": x.nutrition,
                "nutrition_source": x.nutrition_source,
                "version": x.version,
            }

        def _plan_dict(p: PlanVersion | None) -> dict | None:
            if p is None:
                return None
            return {
                "id": str(p.id),
                "sequence_number": p.sequence_number,
                "status": p.status,
                "content": p.content,
                "activated_at": p.activated_at.isoformat() if p.activated_at else None,
            }

        def _profile_dict(pr: Profile | None) -> dict | None:
            if pr is None:
                return None
            return {
                "version": pr.version,
                "goal": pr.goal,
                "height_cm": pr.height_cm,
                "training_experience_months": pr.training_experience_months,
                "sessions_per_week": pr.sessions_per_week,
                "minutes_per_session": pr.minutes_per_session,
                "available_weekdays": pr.available_weekdays,
                "equipment": pr.equipment,
                "available_load_increments": pr.available_load_increments,
            }

        return {
            "generated_at": datetime.now(tz=None),
            "planning_revision": state.planning_revision,
            "profile": _profile_dict(profile),
            "facts": [
                {
                    "id": str(f.id),
                    "kind": f.kind,
                    "fact_key": f.fact_key,
                    "value": f.value,
                    "provenance": f.provenance,
                }
                for f in facts
            ],
            "active_plan": _plan_dict(active_plan),
            "exercises": [
                {
                    "id": str(e.id),
                    "slug": e.slug,
                    "content_version": e.content_version,
                    "name": e.name,
                    "aliases": e.aliases,
                    "movement_pattern": e.movement_pattern,
                    "equipment_tags": e.equipment_tags,
                    "metric_type": e.metric_type,
                    "load_mode": e.load_mode,
                    "instructions": e.instructions,
                    "common_errors": e.common_errors,
                }
                for e in exercises
            ],
            "recent_sessions": [_session_dict(s) for s in recent_sessions],
            "recent_measurements": [_measurement_dict(m) for m in measurements],
            "recent_meals": [_meal_dict(x) for x in meals],
        }
