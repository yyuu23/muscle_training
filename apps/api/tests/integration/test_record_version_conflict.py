"""
Record version conflict tests (plan §12.2): optimistic locking on
online corrections; corrections mark old reviews stale.
"""

import uuid
from datetime import UTC, datetime

import pytest

from app.db.models.training import SessionExercise, WorkoutSession, WorkoutSet
from app.modules.workouts.service import WorkoutService
from tests.integration.conftest import register_user

pytestmark = pytest.mark.integration


async def _seed_record(db, user_id):
    session = WorkoutSession(
        id=uuid.uuid4(), user_id=user_id, started_at=datetime.now(UTC),
        status="in_progress", version=1,
    )
    db.add(session)
    await db.flush()  # parent row first: FK ordering must be explicit

    exercise = SessionExercise(
        id=uuid.uuid4(), user_id=user_id, session_id=session.id, exercise_id=uuid.uuid4(),
        position=0, completion_status="not_recorded", version=1,
    )
    db.add(exercise)
    await db.flush()

    workout_set = WorkoutSet(
        id=uuid.uuid4(), user_id=user_id, session_exercise_id=exercise.id, set_index=1,
        set_kind="work", status="completed", reps=10, version=1,
        performed_at=datetime.now(UTC),
    )
    db.add(workout_set)
    await db.commit()
    return session, exercise, workout_set


@pytest.mark.asyncio
async def test_wrong_expected_version_conflicts(db, http):
    user_id, _, _ = await register_user(http, f"vc-{uuid.uuid4().hex[:8]}")
    uid = uuid.UUID(user_id)
    _, _, workout_set = await _seed_record(db, uid)

    service = WorkoutService(db)
    with pytest.raises(Exception) as exc:
        await service.patch_set(workout_set.id, uid, expected_version=99, reps=8, reason="更正")
    assert exc.value.code == "VERSION_CONFLICT"


@pytest.mark.asyncio
async def test_correct_version_updates_and_records_revision(db, http):
    user_id, _, _ = await register_user(http, f"vc2-{uuid.uuid4().hex[:8]}")
    uid = uuid.UUID(user_id)
    _, _, workout_set = await _seed_record(db, uid)

    service = WorkoutService(db)
    updated = await service.patch_set(
        workout_set.id, uid, expected_version=1, reps=8, reason="记错了，是8次"
    )
    assert updated.version == 2
    assert updated.reps == 8

    from sqlalchemy import select

    from app.db.models.training import RecordRevision

    revisions = (
        await db.execute(
            select(RecordRevision).where(RecordRevision.entity_id == workout_set.id)
        )
    ).scalars().all()
    assert len(revisions) == 1
    assert "reps" in revisions[0].changed_fields
