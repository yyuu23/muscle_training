"""
Plan activation conflict tests (plan §5.9 / §12.2): stale basis
rejects activation; success supersedes the old active plan; at most
one active plan per user.
"""

import uuid

import pytest

from app.db.models.catalog import Exercise, PlanVersion
from app.modules.plans.schemas import PlanContent
from app.modules.plans.service import PlanService
from app.modules.profiles.schemas import ProfileUpdateRequest
from app.modules.profiles.service import ProfileService
from tests.integration.conftest import register_user

pytestmark = pytest.mark.integration


def _seed(user_id):
    """Register already created the user's Profile; only the exercise is seeded.
    equipment_tags=[] keeps the draft validator happy (profile has no equipment yet)."""
    exercise = Exercise(
        slug="squat", content_version=1, name="深蹲", equipment_tags=[], metric_type="reps",
        load_mode="total_external", instructions=[], common_errors=[], approved_alternatives=[],
        evidence_refs=[], review_status="approved", fixture=False,
    )
    return exercise


def _content(exercise_id) -> PlanContent:
    return PlanContent.model_validate({
        "title": "计划", "goal": "力量", "timezone": "Asia/Shanghai",
        "days": [
            {
                "day_key": "day_1", "weekday": 1, "estimated_minutes": 60,
                "exercises": [{
                    "item_id": "i1", "exercise_id": str(exercise_id), "exercise_content_version": 1,
                    "working_sets": 3, "reps_min": 8, "reps_max": 12, "rest_seconds": 120,
                }],
            },
            {
                "day_key": "day_2", "weekday": 4, "estimated_minutes": 60,
                "exercises": [{
                    "item_id": "i2", "exercise_id": str(exercise_id), "exercise_content_version": 1,
                    "working_sets": 3, "reps_min": 8, "reps_max": 12, "rest_seconds": 120,
                }],
            },
        ],
    })


@pytest.mark.asyncio
async def test_stale_basis_rejects_activation(db, http):
    user_id, _, _ = await register_user(http, f"plan-{uuid.uuid4().hex[:8]}")
    uid = uuid.UUID(user_id)
    exercise = _seed(uid)
    db.add(exercise)
    await db.commit()

    service = PlanService(db)
    draft = await service.create_draft(uid, content=_content(exercise.id), template_versions=None, model_run_id=None, rationale=None)

    # Basis drifts: profile edit bumps planning_revision
    profile_service = ProfileService(db)
    await profile_service.update_profile(
        uid, ProfileUpdateRequest(expected_version=1, sessions_per_week=2, goal="增肌")
    )

    with pytest.raises(Exception) as exc:
        await service.activate_plan(
            draft.id, uid,
            expected_basis_planning_revision=1,  # the revision the client saw
        )
    assert exc.value.code == "PLAN_CONTEXT_STALE"


@pytest.mark.asyncio
async def test_activation_supersedes_previous_active(db, http):
    user_id, _, _ = await register_user(http, f"plan2-{uuid.uuid4().hex[:8]}")
    uid = uuid.UUID(user_id)
    exercise = _seed(uid)
    db.add(exercise)
    await db.commit()

    service = PlanService(db)
    from app.services.planning import get_user_state

    state = await get_user_state(db, uid)

    first = await service.create_draft(uid, content=_content(exercise.id), template_versions=None, model_run_id=None, rationale=None)
    revision = state.planning_revision
    activated, superseded = await service.activate_plan(
        first.id, uid, expected_basis_planning_revision=revision
    )
    assert activated.status == "active"
    assert superseded is None

    # Second draft generated on the new basis
    second = await service.create_draft(uid, content=_content(exercise.id), template_versions=None, model_run_id=None, rationale=None)
    state = await get_user_state(db, uid)
    activated2, superseded2 = await service.activate_plan(
        second.id, uid, expected_basis_planning_revision=state.planning_revision
    )
    assert activated2.status == "active"
    assert superseded2 is not None and superseded2.id == first.id

    # Exactly one active plan remains
    from sqlalchemy import select

    active = (
        await db.execute(
            select(PlanVersion).where(PlanVersion.user_id == uid).where(PlanVersion.status == "active")
        )
    ).scalars().all()
    assert len(active) == 1
    assert active[0].id == second.id
