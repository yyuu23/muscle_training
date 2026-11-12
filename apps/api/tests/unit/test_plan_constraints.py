"""
Plan constraint tests (plan §5.4 / §7.4): PlanContent mutual exclusion
and validators (catalog/equipment/exclusion/ranges/fixture rules).
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.plans.schemas import PlanContent, PlanExerciseItem


def _exercise_item(**overrides) -> dict:
    base = {
        "item_id": "item-1",
        "exercise_id": uuid.uuid4(),
        "exercise_content_version": 1,
        "working_sets": 3,
        "reps_min": 8,
        "reps_max": 12,
        "rest_seconds": 120,
        "target_rir": 2,
        "initial_load_kg": None,
    }
    base.update(overrides)
    return base


def _day(**overrides) -> dict:
    base = {"day_key": "day_1", "weekday": 1, "estimated_minutes": 60, "exercises": [_exercise_item()]}
    base.update(overrides)
    return base


def test_reps_and_duration_are_exclusive():
    with pytest.raises(ValueError, match="互斥"):
        PlanExerciseItem.model_validate(_exercise_item(duration_seconds=45))


def test_neither_reps_nor_duration_rejected():
    item = _exercise_item()
    del item["reps_min"]
    del item["reps_max"]
    with pytest.raises(ValueError, match="之一"):
        PlanExerciseItem.model_validate(item)


def test_reps_range_min_le_max():
    with pytest.raises(ValueError):
        PlanExerciseItem.model_validate(_exercise_item(reps_min=12, reps_max=8))


def test_reps_range_requires_both_bounds():
    item = _exercise_item()
    del item["reps_max"]
    with pytest.raises(ValueError, match="同时"):
        PlanExerciseItem.model_validate(item)


def test_day_keys_must_be_unique():
    with pytest.raises(ValueError, match="重复"):
        PlanContent.model_validate(
            {
                "title": "计划",
                "goal": "力量",
                "timezone": "Asia/Shanghai",
                "days": [_day(), _day()],
            }
        )


def test_valid_plan_content_parses():
    content = PlanContent.model_validate(
        {
            "title": "新手全身计划",
            "goal": "建立基础力量",
            "timezone": "Asia/Shanghai",
            "days": [
                _day(),
                _day(day_key="day_2", weekday=4),
            ],
        }
    )
    assert len(content.days) == 2
    assert content.days[0].exercises[0].initial_load_kg is None


# ---------------------------------------------------------------------------
# Domain validators (DB mocked)
# ---------------------------------------------------------------------------


def _mock_db(exercises, facts=(), profile=None):
    """AsyncMock db where each execute returns a scalar-result-like object."""

    class Result:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

        def scalars(self):
            return self

        def all(self):
            return list(self._value)

    values = iter([exercises, facts, profile])
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=lambda q: Result(next(values)))
    return db


def _catalog_exercise(slug="squat", name="深蹲", fixture=False, equipment=None, status="approved"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        slug=slug,
        name=name,
        fixture=fixture,
        review_status=status,
        content_version=1,
        equipment_tags=equipment or ["barbell"],
        metric_type="reps",
    )


def _fact(kind="exercise_exclusion", key="squat"):
    return SimpleNamespace(kind=kind, fact_key=key)


def _profile(equipment=None, sessions_per_week=3, minutes=60, weekdays=None):
    return SimpleNamespace(
        equipment=equipment,
        sessions_per_week=sessions_per_week,
        minutes_per_session=minutes,
        available_weekdays=weekdays or [1, 2, 3, 4, 5, 6, 7],
    )


@pytest.mark.asyncio
async def test_unknown_exercise_flagged(monkeypatch):
    from app.modules.plans import validators

    monkeypatch.setattr(validators, "get_settings", lambda: SimpleNamespace(python_env="development"))
    content = PlanContent.model_validate(
        {"title": "t", "goal": "g", "timezone": "Asia/Shanghai", "days": [_day()]}
    )
    db = _mock_db(exercises=[])  # no exercise found
    issues = await validators.validate_plan_content(db, uuid.uuid4(), content, None)
    assert any(i.code == "exercise_not_found" for i in issues)


@pytest.mark.asyncio
async def test_fixture_blocked_in_production(monkeypatch):
    from app.modules.plans import validators

    monkeypatch.setattr(validators, "get_settings", lambda: SimpleNamespace(python_env="production"))
    exercise = _catalog_exercise(fixture=True)
    content = PlanContent.model_validate(
        {
            "title": "t", "goal": "g", "timezone": "Asia/Shanghai",
            "days": [
                _day(exercises=[_exercise_item(exercise_id=exercise.id)]),
            ],
        }
    )
    db = _mock_db(exercises=[exercise])
    issues = await validators.validate_plan_content(db, uuid.uuid4(), content, None)
    assert any(i.code == "fixture_in_production" for i in issues)


@pytest.mark.asyncio
async def test_equipment_mismatch_flagged(monkeypatch):
    from app.modules.plans import validators

    monkeypatch.setattr(validators, "get_settings", lambda: SimpleNamespace(python_env="development"))
    exercise = _catalog_exercise(equipment=["barbell", "bench"])
    content = PlanContent.model_validate(
        {
            "title": "t", "goal": "g", "timezone": "Asia/Shanghai",
            "days": [_day(exercises=[_exercise_item(exercise_id=exercise.id)])],
        }
    )
    db = _mock_db(exercises=[exercise], profile=_profile(equipment=["dumbbell"]))
    issues = await validators.validate_plan_content(db, uuid.uuid4(), content, None)
    assert any(i.code == "equipment_mismatch" for i in issues)


@pytest.mark.asyncio
async def test_user_excluded_exercise_flagged(monkeypatch):
    from app.modules.plans import validators

    monkeypatch.setattr(validators, "get_settings", lambda: SimpleNamespace(python_env="development"))
    exercise = _catalog_exercise(slug="squat")
    content = PlanContent.model_validate(
        {
            "title": "t", "goal": "g", "timezone": "Asia/Shanghai",
            "days": [_day(exercises=[_exercise_item(exercise_id=exercise.id)])],
        }
    )
    db = _mock_db(exercises=[exercise], facts=[_fact(key=exercise.slug)])
    issues = await validators.validate_plan_content(db, uuid.uuid4(), content, None)
    assert any(i.code == "exercise_excluded_by_user" for i in issues)


@pytest.mark.asyncio
async def test_profile_time_and_day_budget(monkeypatch):
    from app.modules.plans import validators

    monkeypatch.setattr(validators, "get_settings", lambda: SimpleNamespace(python_env="development"))
    exercise = _catalog_exercise(equipment=[])
    item = _exercise_item(exercise_id=exercise.id)
    content = PlanContent.model_validate(
        {
            "title": "t", "goal": "g", "timezone": "Asia/Shanghai",
            "days": [
                _day(day_key="day_1", weekday=1, estimated_minutes=60, exercises=[item]),
                _day(day_key="day_2", weekday=2, estimated_minutes=60, exercises=[dict(item, item_id="i2")]),
                _day(day_key="day_3", weekday=6, estimated_minutes=90, exercises=[dict(item, item_id="i3")]),
            ],
        }
    )
    db = _mock_db(
        exercises=[exercise],
        profile=_profile(equipment=[], sessions_per_week=2, minutes=60, weekdays=[1]),
    )
    issues = await validators.validate_plan_content(db, uuid.uuid4(), content, None)
    codes = {i.code for i in issues}
    assert "too_many_days_for_profile" in codes  # 3 days > 2/week
    assert "session_too_long" in codes           # 90min > 60min
    assert "weekday_not_available" in codes      # weekday 2 & 6 not in [1]
