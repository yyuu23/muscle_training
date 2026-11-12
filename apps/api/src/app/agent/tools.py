"""
Typed read-only business tools (plan §4.4)

User identity is injected by the backend; tools cannot act as another
user, cannot write business tables, and every call counts against the
tool budget.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.limits import BudgetTracker
from app.db.models.catalog import Exercise, PlanVersion
from app.db.models.nutrition import Measurement
from app.db.models.training import SessionExercise, WorkoutSession, WorkoutSet


class ToolError(Exception):
    """Tool-level failure surfaced to the orchestrator."""


class AgentTools:
    """Read-only tools with an injected user scope."""

    def __init__(self, db: AsyncSession, user_id: UUID, budget: BudgetTracker):
        self.db = db
        self.user_id = user_id
        self.budget = budget

    def _charge(self) -> None:
        self.budget.check_tool_call()
        self.budget.record_tool_call()

    async def get_recent_training(self, limit: int = 5) -> list[dict]:
        """Recent sessions with sets, strictly scoped to the user."""
        self._charge()
        sessions = (
            await self.db.execute(
                select(WorkoutSession)
                .where(WorkoutSession.user_id == self.user_id)
                .order_by(WorkoutSession.started_at.desc())
                .limit(min(limit, 10))
            )
        ).scalars().all()

        results = []
        for session in sessions:
            exercises = (
                await self.db.execute(
                    select(SessionExercise).where(SessionExercise.session_id == session.id)
                )
            ).scalars().all()
            sets = (
                await self.db.execute(
                    select(WorkoutSet)
                    .where(WorkoutSet.user_id == self.user_id)
                    .where(WorkoutSet.session_exercise_id.in_([e.id for e in exercises] or [None]))
                )
            ).scalars().all()
            results.append(
                {
                    "started_at": session.started_at.isoformat(),
                    "status": session.status,
                    "exercise_count": len(exercises),
                    "set_count": len(sets),
                    "notes": session.notes,
                }
            )
        return results

    async def get_exercise_info(self, exercise_id: UUID) -> dict:
        """Exercise card: instructions, errors, alternatives."""
        self._charge()
        exercise = await self.db.get(Exercise, exercise_id)
        if exercise is None:
            raise ToolError("动作不存在")
        return {
            "name": exercise.name,
            "slug": exercise.slug,
            "instructions": exercise.instructions,
            "common_errors": exercise.common_errors,
            "approved_alternatives": exercise.approved_alternatives,
            "metric_type": exercise.metric_type,
            "load_mode": exercise.load_mode,
        }

    async def get_active_plan(self) -> dict | None:
        """Current plan summary (never another user's)."""
        self._charge()
        plan = (
            await self.db.execute(
                select(PlanVersion)
                .where(PlanVersion.user_id == self.user_id)
                .where(PlanVersion.status == "active")
            )
        ).scalar_one_or_none()
        if plan is None:
            return None
        return {"id": str(plan.id), "title": plan.content.get("title"), "days": len(plan.content.get("days", []))}

    async def get_recent_measurements(self, measurement_type: str = "weight", limit: int = 10) -> list[dict]:
        """Precise record queries — vector search never substitutes these."""
        self._charge()
        rows = (
            await self.db.execute(
                select(Measurement)
                .where(Measurement.user_id == self.user_id)
                .where(Measurement.measurement_type == measurement_type)
                .order_by(Measurement.observed_at.desc())
                .limit(min(limit, 30))
            )
        ).scalars().all()
        return [
            {"observed_at": m.observed_at.isoformat(), "value": str(m.value), "unit": m.unit}
            for m in rows
        ]

    async def search_knowledge(self, query: str) -> list[dict]:
        """Permission-filtered hybrid retrieval (rag.retrieval)."""
        self._charge()
        from app.rag.retrieval import hybrid_search

        chunks = await hybrid_search(self.db, self.user_id, query, final_limit=6)
        return [
            {
                "chunk_id": str(c.chunk_id),
                "title": c.title,
                "start_ms": c.start_ms,
                "end_ms": c.end_ms,
                "text": c.display_text,
            }
            for c in chunks
        ]
