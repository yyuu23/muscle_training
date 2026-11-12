"""
Context builder (plan §7.3)

Builds the ContextBundle and trims to the token budget.

Trim order:
1. drop unrelated chat history
2. drop low-ranked knowledge chunks
3. drop unrelated raw training records
4. keep necessary statistics and latest facts

Never trimmed: confirmed constraints, task-relevant discomfort,
equipment/time constraints, current plan and basis versions. When the
must-keep content alone exceeds the budget, raise an explainable error
instead of silently dropping constraints.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, ErrorCode
from app.db.models.catalog import PlanVersion
from app.db.models.operations import Conversation, Message
from app.db.models.profile import Profile, ProfileFact
from app.db.models.training import SessionExercise, WorkoutSession, WorkoutSet
from app.services.planning import get_user_state

ROUGH_TOKENS_PER_CHAR = 0.6  # conservative for Chinese + JSON


@dataclass
class KnowledgeEvidence:
    chunk_id: str
    title: str
    start_ms: int | None
    end_ms: int | None
    text: str


@dataclass
class RawRecord:
    session_id: str
    started_at: str
    summary: str


@dataclass
class ContextBundle:
    request_id: str
    task_type: str
    user_timezone: str
    profile_version: int | None
    planning_revision: int
    confirmed_profile: dict
    confirmed_constraints: list[dict] = field(default_factory=list)
    unresolved_recent_reports: list[dict] = field(default_factory=list)
    active_plan_id: str | None = None
    active_plan_summary: dict | None = None
    recent_training_summary: dict = field(default_factory=dict)
    relevant_raw_records: list[RawRecord] = field(default_factory=list)
    knowledge_evidence: list[KnowledgeEvidence] = field(default_factory=list)
    recent_chat: list[dict] = field(default_factory=list)
    data_cutoff_at: datetime = field(default_factory=datetime.now)

    def estimate_tokens(self) -> int:
        import json

        payload = json.dumps(self.__dict__, ensure_ascii=False, default=str)
        return int(len(payload) * ROUGH_TOKENS_PER_CHAR)


async def build_context(
    db: AsyncSession,
    user_id: UUID,
    *,
    task_type: str,
    request_id: str,
    knowledge: list[KnowledgeEvidence] | None = None,
    max_context_tokens: int = 12000,
) -> ContextBundle:
    """Assemble the ContextBundle from confirmed data (plan §7.3)."""
    from app.db.models.auth import User

    user = await db.get(User, user_id)
    state = await get_user_state(db, user_id)
    profile = (
        await db.execute(select(Profile).where(Profile.user_id == user_id))
    ).scalar_one_or_none()

    # Confirmed constraints: active facts (preferences/limits/allergies)
    facts = (
        await db.execute(
            select(ProfileFact)
            .where(ProfileFact.user_id == user_id)
            .where(ProfileFact.superseded_by.is_(None))
        )
    ).scalars().all()

    confirmed_constraints = [
        {"kind": f.kind, "fact_key": f.fact_key, "value": f.value, "provenance": f.provenance}
        for f in facts
        if f.kind in ("training_limitation", "exercise_exclusion", "allergy_report", "unresolved_discomfort")
    ]
    unresolved = [
        {"kind": f.kind, "fact_key": f.fact_key, "value": f.value}
        for f in facts
        if f.kind == "unresolved_discomfort"
    ]

    # Active plan summary
    active_plan = (
        await db.execute(
            select(PlanVersion)
            .where(PlanVersion.user_id == user_id)
            .where(PlanVersion.status == "active")
        )
    ).scalar_one_or_none()
    plan_summary = None
    if active_plan is not None:
        content = active_plan.content or {}
        plan_summary = {
            "title": content.get("title"),
            "days": [
                {
                    "day_key": d.get("day_key"),
                    "weekday": d.get("weekday"),
                    "estimated_minutes": d.get("estimated_minutes"),
                    "exercises": [
                        {"item_id": e.get("item_id"), "sets": e.get("working_sets")}
                        for e in d.get("exercises", [])
                    ],
                }
                for d in content.get("days", [])
            ],
        }

    # Recent training (last 30 days), compact summaries only
    cutoff = datetime.now(tz=None) - timedelta(days=30)
    sessions = (
        await db.execute(
            select(WorkoutSession)
            .where(WorkoutSession.user_id == user_id)
            .where(WorkoutSession.started_at >= cutoff)
            .order_by(WorkoutSession.started_at.desc())
            .limit(10)
        )
    ).scalars().all()

    raw_records: list[RawRecord] = []
    total_sets = 0
    for session in sessions:
        exercises = (
            await db.execute(
                select(SessionExercise).where(SessionExercise.session_id == session.id)
            )
        ).scalars().all()
        set_rows = (
            await db.execute(
                select(WorkoutSet)
                .where(WorkoutSet.user_id == user_id)
                .where(
                    WorkoutSet.session_exercise_id.in_([e.id for e in exercises] or [None])
                )
            )
        ).scalars().all()
        total_sets += len(set_rows)
        raw_records.append(
            RawRecord(
                session_id=str(session.id),
                started_at=session.started_at.isoformat(),
                summary=f"{len(exercises)} 个动作 / {len(set_rows)} 组 / 状态 {session.status}",
            )
        )

    recent_training_summary = {
        "sessions_last_30d": len(sessions),
        "total_sets_last_30d": total_sets,
    }

    # Recent chat history (trimmed first)
    conversations = (
        await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )
    ).scalars().all()
    recent_chat: list[dict] = []
    if conversations:
        messages = (
            await db.execute(
                select(Message)
                .where(Message.conversation_id == conversations[0].id)
                .order_by(Message.created_at.desc())
                .limit(6)
            )
        ).scalars().all()
        recent_chat = [
            {"role": m.role, "content": m.content[:200]} for m in reversed(list(messages))
        ]

    bundle = ContextBundle(
        request_id=request_id,
        task_type=task_type,
        user_timezone=user.timezone if user else "Asia/Shanghai",
        profile_version=profile.version if profile else None,
        planning_revision=state.planning_revision,
        confirmed_profile={
            "goal": profile.goal if profile else None,
            "sessions_per_week": profile.sessions_per_week if profile else None,
            "minutes_per_session": profile.minutes_per_session if profile else None,
            "equipment": profile.equipment if profile else None,
            "available_weekdays": profile.available_weekdays if profile else None,
            "training_experience_months": profile.training_experience_months if profile else None,
        },
        confirmed_constraints=confirmed_constraints,
        unresolved_recent_reports=unresolved,
        active_plan_id=str(state.active_plan_id) if state.active_plan_id else None,
        active_plan_summary=plan_summary,
        recent_training_summary=recent_training_summary,
        relevant_raw_records=raw_records,
        knowledge_evidence=knowledge or [],
        recent_chat=recent_chat,
    )

    return trim_to_budget(bundle, max_context_tokens)


def trim_to_budget(bundle: ContextBundle, max_context_tokens: int) -> ContextBundle:
    """Trim in the fixed order; constraints are never dropped (plan §7.3)."""
    # 1. Drop unrelated chat history first
    if bundle.estimate_tokens() > max_context_tokens:
        bundle.recent_chat = []

    # 2. Drop low-ranked knowledge chunks (evidence arrives ranked)
    if bundle.estimate_tokens() > max_context_tokens:
        while bundle.knowledge_evidence and bundle.estimate_tokens() > max_context_tokens:
            bundle.knowledge_evidence.pop()

    # 3. Drop unrelated raw records (oldest first)
    if bundle.estimate_tokens() > max_context_tokens:
        while bundle.relevant_raw_records and bundle.estimate_tokens() > max_context_tokens:
            bundle.relevant_raw_records.pop(0)

    # Must-keep content (constraints + plan basis) still over budget → error
    if bundle.estimate_tokens() > max_context_tokens:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR,
            "必要上下文（已确认限制与计划依据）超过预算，请缩小问题范围",
        )
    return bundle
