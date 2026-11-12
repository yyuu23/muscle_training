"""
Plan generation handler (plan §7.4)

Short-tx read basis → release tx → model call → validation → save
immutable draft. Model failures never touch existing plans.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import Orchestrator
from app.api.errors import ApiError, ErrorCode
from app.db.models.catalog import Exercise
from app.jobs.queue import complete_job, fail_job

logger = logging.getLogger(__name__)


async def handle_plan_generate(db: AsyncSession, job) -> None:
    user_id = UUID(job.payload["user_id"])

    orchestrator = Orchestrator(db, user_id, request_id=str(job.id))
    try:
        result = await orchestrator.generate_plan_candidate()
    except ApiError as exc:
        await fail_job(
            db,
            job.id,
            error_code=exc.code,
            error_detail=exc.message,
            retryable=exc.code in ("MODEL_UNAVAILABLE", "MODEL_TIMEOUT", "RATE_LIMITED"),
        )
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("plan generation failed")
        await fail_job(db, job.id, error_code="PLAN_GENERATION_ERROR", error_detail=str(exc)[:500])
        return

    candidate = result.pop("candidate")
    from app.modules.plans.service import PlanService

    try:
        content = await _candidate_to_content(db, candidate)
        service = PlanService(db)
        draft = await service.create_draft(
            user_id,
            content=content,
            template_versions=[
                {"template_id": result["template_id"], "content_version": result["template_version"]}
            ],
            model_run_id=None,
            rationale=candidate.get("notes"),
        )
    except ApiError as exc:
        await fail_job(db, job.id, error_code=exc.code, error_detail=exc.message, retryable=False)
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("plan draft save failed")
        await fail_job(db, job.id, error_code="PLAN_SAVE_ERROR", error_detail=str(exc)[:500])
        return

    await complete_job(db, job.id, {"plan_draft_id": str(draft.id)})


async def _candidate_to_content(db: AsyncSession, candidate: dict):
    """Map PlanCandidate output into PlanContent, resolving slugs to
    catalog exercise ids + content versions."""
    from app.modules.plans.schemas import PlanContent, PlanDay, PlanExerciseItem

    slugs = {item["exercise_slug"] for day in candidate["days"] for item in day["exercises"]}
    if not slugs:
        raise ApiError(ErrorCode.MODEL_OUTPUT_INVALID, "计划候选没有动作")

    rows = (
        await db.execute(
            select(Exercise).where(Exercise.slug.in_(slugs)).where(Exercise.review_status == "approved")
        )
    ).scalars().all()
    by_slug: dict[str, Exercise] = {}
    for exercise in rows:
        current = by_slug.get(exercise.slug)
        if current is None or exercise.content_version > current.content_version:
            by_slug[exercise.slug] = exercise

    days = []
    for day in candidate["days"]:
        exercises = []
        for item in day["exercises"]:
            slug = item["exercise_slug"]
            exercise = by_slug.get(slug)
            if exercise is None:
                raise ApiError(
                    ErrorCode.MODEL_OUTPUT_INVALID,
                    f"动作 {slug} 不在已审核目录中",
                )
            exercises.append(
                PlanExerciseItem(
                    item_id=f"{day['day_key']}-{slug}-{len(exercises) + 1}",
                    exercise_id=exercise.id,
                    exercise_content_version=exercise.content_version,
                    exercise_snapshot={
                        "slug": exercise.slug,
                        "name": exercise.name,
                        "metric_type": exercise.metric_type,
                        "load_mode": exercise.load_mode,
                    },
                    working_sets=item["working_sets"],
                    reps_min=item.get("reps_min"),
                    reps_max=item.get("reps_max"),
                    duration_seconds=item.get("duration_seconds"),
                    rest_seconds=item["rest_seconds"],
                    target_rir=item.get("target_rir"),
                    initial_load_kg=item.get("initial_load_kg"),
                    load_instruction=item.get("load_instruction"),
                )
            )
        days.append(
            PlanDay(
                day_key=day["day_key"],
                weekday=day["weekday"],
                estimated_minutes=day["estimated_minutes"],
                warmup_steps=[],
                exercises=exercises,
                completion_questions=[],
            )
        )

    return PlanContent(
        title=candidate["title"],
        goal=candidate["goal"],
        timezone="Asia/Shanghai",
        days=days,
        notes=candidate.get("notes"),
    )
