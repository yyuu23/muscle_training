"""
Plan domain validators (plan §7.4)

Program-checkable constraints only: existence, review status, fixture
exclusion, equipment, time budget, set/rep/rest ranges, exclusions,
reference legality, no fabricated loads. Passing these checks never
claims medical validity of the prescription.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.catalog import Exercise, TrainingTemplate
from app.db.models.profile import Profile, ProfileFact
from app.modules.plans.schemas import PlanContent, PlanValidationIssue


async def validate_plan_content(
    db: AsyncSession,
    user_id: UUID,
    content: PlanContent,
    template: TrainingTemplate | None,
) -> list[PlanValidationIssue]:
    """Validate a plan candidate against catalog data and user constraints."""
    issues: list[PlanValidationIssue] = []
    settings = get_settings()
    production = settings.python_env == "production"

    # Load exercises referenced by the plan
    exercise_ids = {item.exercise_id for day in content.days for item in day.exercises}
    exercises: dict[UUID, Exercise] = {}
    if exercise_ids:
        result = await db.execute(select(Exercise).where(Exercise.id.in_(exercise_ids)))
        exercises = {e.id: e for e in result.scalars().all()}

    # User-excluded exercise fact keys (kind=exercise_exclusion)
    exclusion_result = await db.execute(
        select(ProfileFact)
        .where(ProfileFact.user_id == user_id)
        .where(ProfileFact.kind == "exercise_exclusion")
        .where(ProfileFact.superseded_by.is_(None))
    )
    excluded_keys = {f.fact_key for f in exclusion_result.scalars().all()}

    profile = (await db.execute(select(Profile).where(Profile.user_id == user_id))).scalar_one_or_none()

    total_days = len(content.days)
    weekday_counts: dict[int, int] = {}
    equipment_by_day: dict[str, set] = {}

    for day in content.days:
        weekday_counts[day.weekday] = weekday_counts.get(day.weekday, 0) + 1
        for item in day.exercises:
            exercise = exercises.get(item.exercise_id)

            if exercise is None:
                issues.append(
                    PlanValidationIssue(
                        code="exercise_not_found",
                        message=f"动作 {item.exercise_id} 不存在",
                        item_id=item.item_id,
                    )
                )
                continue

            if exercise.review_status != "approved":
                issues.append(
                    PlanValidationIssue(
                        code="exercise_not_approved",
                        message=f"动作 {exercise.name} 未通过审核",
                        item_id=item.item_id,
                    )
                )

            if exercise.fixture and production:
                issues.append(
                    PlanValidationIssue(
                        code="fixture_in_production",
                        message=f"测试动作 {exercise.name} 不能进入生产计划",
                        item_id=item.item_id,
                    )
                )

            if item.exercise_content_version != exercise.content_version:
                issues.append(
                    PlanValidationIssue(
                        code="exercise_version_mismatch",
                        message=f"动作 {exercise.name} 的内容版本与快照不一致",
                        item_id=item.item_id,
                    )
                )

            # Equipment match
            needed = set(exercise.equipment_tags or [])
            available = set((profile.equipment if profile and profile.equipment else []) or [])
            if needed and not needed.issubset(available):
                issues.append(
                    PlanValidationIssue(
                        code="equipment_mismatch",
                        message=f"动作 {exercise.name} 需要器械 {sorted(needed - available)}",
                        item_id=item.item_id,
                    )
                )
            equipment_by_day.setdefault(day.day_key, set()).update(needed)

            # User exclusion
            for key in (exercise.slug, exercise.name, str(exercise.id)):
                if key in excluded_keys:
                    issues.append(
                        PlanValidationIssue(
                            code="exercise_excluded_by_user",
                            message=f"用户已明确排除动作 {exercise.name}",
                            item_id=item.item_id,
                        )
                    )

            # Metric type consistency
            if exercise.metric_type == "reps" and item.duration_seconds is not None:
                issues.append(
                    PlanValidationIssue(
                        code="metric_type_mismatch",
                        message=f"动作 {exercise.name} 是次数型，不能使用时长目标",
                        item_id=item.item_id,
                    )
                )
            if exercise.metric_type == "duration" and item.reps_min is not None:
                issues.append(
                    PlanValidationIssue(
                        code="metric_type_mismatch",
                        message=f"动作 {exercise.name} 是时长型，不能使用次数目标",
                        item_id=item.item_id,
                    )
                )

    # Template-level checks
    if template is not None:
        if template.review_status != "approved":
            issues.append(
                PlanValidationIssue(code="template_not_approved", message="模板未通过审核")
            )
        if template.fixture and production:
            issues.append(
                PlanValidationIssue(code="fixture_in_production", message="测试模板不能进入生产")
            )
        if total_days != template.sessions_per_week:
            issues.append(
                PlanValidationIssue(
                    code="day_count_mismatch",
                    message=f"训练天数 {total_days} 与模板要求 {template.sessions_per_week} 不符",
                )
            )

        allowed_ids = set(template.allowed_exercise_ids or [])
        if allowed_ids:
            for item in (i for d in content.days for i in d.exercises):
                if item.exercise_id not in allowed_ids:
                    issues.append(
                        PlanValidationIssue(
                            code="exercise_outside_template",
                            message=f"动作 {item.exercise_id} 不在模板允许范围内",
                            item_id=item.item_id,
                        )
                    )

        set_ranges = template.allowed_set_ranges or {}
        if "min" in set_ranges and "max" in set_ranges:
            for item in (i for d in content.days for i in d.exercises):
                if not (set_ranges["min"] <= item.working_sets <= set_ranges["max"]):
                    issues.append(
                        PlanValidationIssue(
                            code="set_count_out_of_range",
                            message=f"{item.item_id} 组数 {item.working_sets} 超出模板范围",
                            item_id=item.item_id,
                        )
                    )

        rep_ranges = template.allowed_rep_ranges or {}
        if "min" in rep_ranges and "max" in rep_ranges:
            for item in (i for d in content.days for i in d.exercises):
                if item.reps_min is not None and item.reps_max is not None:
                    if not (
                        rep_ranges["min"] <= item.reps_min
                        and item.reps_max <= rep_ranges["max"]
                        and item.reps_min <= item.reps_max
                    ):
                        issues.append(
                            PlanValidationIssue(
                                code="rep_range_out_of_range",
                                message=f"{item.item_id} 次数范围超出模板允许",
                                item_id=item.item_id,
                            )
                        )

        rest_ranges = template.allowed_rest_ranges or {}
        if "min" in rest_ranges and "max" in rest_ranges:
            for item in (i for d in content.days for i in d.exercises):
                if not (rest_ranges["min"] <= item.rest_seconds <= rest_ranges["max"]):
                    issues.append(
                        PlanValidationIssue(
                            code="rest_out_of_range",
                            message=f"{item.item_id} 休息时间超出模板允许",
                            item_id=item.item_id,
                        )
                    )

    # Profile time budget
    if profile is not None and profile.sessions_per_week is not None:
        if total_days > profile.sessions_per_week:
            issues.append(
                PlanValidationIssue(
                    code="too_many_days_for_profile",
                    message=f"计划天数 {total_days} 超过档案设定 {profile.sessions_per_week}",
                )
            )
    if profile is not None and profile.minutes_per_session is not None:
        for day in content.days:
            if day.estimated_minutes > profile.minutes_per_session:
                issues.append(
                    PlanValidationIssue(
                        code="session_too_long",
                        message=f"{day.day_key} 预计 {day.estimated_minutes} 分钟超过档案时间预算",
                    )
                )

    # Available weekdays
    if profile is not None and profile.available_weekdays:
        available_days = set(profile.available_weekdays)
        for day in content.days:
            if day.weekday not in available_days:
                issues.append(
                    PlanValidationIssue(
                        code="weekday_not_available",
                        message=f"{day.day_key} 安排在不可训练的星期 {day.weekday}",
                    )
                )

    return issues
