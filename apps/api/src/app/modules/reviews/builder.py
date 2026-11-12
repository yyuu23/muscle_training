"""
Weekly review builder (plan §7.12)

- Statistics are computed by code; the model only interprets them.
- No training records → fixed "data insufficient" result, no model call.
- Late logs/corrections/deletions mark old reviews stale.
"""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.catalog import PlanVersion
from app.db.models.nutrition import Measurement
from app.db.models.training import SessionExercise, WorkoutSession, WorkoutSet
from app.modules.workouts.statistics import compute_session_stats


def week_start_for(now: datetime) -> datetime:
    """Monday 00:00 of the week containing `now` (natural week, local)."""
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return day - timedelta(days=day.weekday())


async def build_weekly_statistics(db: AsyncSession, user_id: UUID, week_start: datetime) -> dict:
    """Deterministic statistics for one natural week (Mon→Sun)."""
    week_end = week_start + timedelta(days=7)
    data_cutoff = datetime.now(tz=None)

    sessions = (
        await db.execute(
            select(WorkoutSession)
            .where(WorkoutSession.user_id == user_id)
            .where(WeekWindow(WorkoutSession.started_at, week_start, week_end))
            .order_by(WorkoutSession.started_at)
        )
    ).scalars().all()

    session_stats = []
    total_sets = 0
    total_reps = 0
    skipped_exercises = 0
    discomfort_reports: list[str] = []

    for session in sessions:
        exercises = (
            await db.execute(
                select(SessionExercise)
                .where(SessionExercise.session_id == session.id)
                .where(SessionExercise.user_id == user_id)
            )
        ).scalars().all()
        sets = (
            await db.execute(
                select(WorkoutSet)
                .where(WorkoutSet.user_id == user_id)
                .where(WorkoutSet.session_exercise_id.in_([e.id for e in exercises] or [None]))
            )
        ).scalars().all()

        stats = compute_session_stats(session, list(exercises), list(sets))
        session_stats.append(
            {
                "session_id": str(session.id),
                "started_at": session.started_at.isoformat(),
                "status": session.status,
                "duration_minutes": stats.duration_minutes,
                "total_working_sets": stats.total_working_sets,
                "total_working_reps": stats.total_working_reps,
            }
        )
        total_sets += stats.total_working_sets
        total_reps += stats.total_working_reps
        skipped_exercises += sum(1 for e in exercises if e.completion_status == "skipped")
        for ex_stats in stats.exercises:
            discomfort_reports.extend(ex_stats.discomfort_reports)

    # Weight observations this week
    weights = (
        await db.execute(
            select(Measurement)
            .where(Measurement.user_id == user_id)
            .where(Measurement.measurement_type == "weight")
            .where(Measurement.observed_at >= week_start)
            .where(Measurement.observed_at < week_end)
            .order_by(Measurement.observed_at)
        )
    ).scalars().all()
    weight_values = [float(w.value) for w in weights]

    # Planned days from active plan for adherence context
    active_plan = (
        await db.execute(
            select(PlanVersion)
            .where(PlanVersion.user_id == user_id)
            .where(PlanVersion.status == "active")
        )
    ).scalar_one_or_none()
    planned_days = len(active_plan.content.get("days", [])) if active_plan and active_plan.content else None

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "data_cutoff_at": data_cutoff.isoformat(),
        "sessions_completed": sum(1 for s in sessions if s.status == "completed"),
        "sessions_total": len(sessions),
        "planned_days": planned_days,
        "total_working_sets": total_sets,
        "total_working_reps": total_reps,
        "skipped_exercises": skipped_exercises,
        "discomfort_reports": discomfort_reports[:10],
        "weight_count": len(weight_values),
        "weight_first": weight_values[0] if weight_values else None,
        "weight_last": weight_values[-1] if weight_values else None,
        "data_sufficient": len(sessions) > 0,
        "session_details": session_stats,
    }


def WeekWindow(column, week_start: datetime, week_end: datetime):
    """SQLAlchemy filter: value within [week_start, week_end)."""
    from sqlalchemy import and_

    return and_(column >= week_start, column < week_end)


def build_insufficient_data_review(statistics: dict) -> dict:
    """Fixed no-data result: never a model call, never fabricated progress."""
    return {
        "narrative_markdown": (
            "本周没有足够的训练记录，无法生成复盘。\n\n"
            "数据不足时不会生成虚构的进步分析。恢复记录后可重新生成本周复盘。"
        ),
        "data_gaps_acknowledged": True,
        "adjustment_suggestions": [],
    }
