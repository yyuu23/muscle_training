"""
Deletion ledger (plan §9.5)

User deletion covers raw data, memory candidates, summaries, vectors,
revisions and attachments. Restoring an old backup re-applies the
ledger so deletions survive restores.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.catalog import PlanVersion
from app.db.models.knowledge import Asset, KnowledgeChunk, KnowledgeSource, SourceRevision
from app.db.models.nutrition import MealLog, Measurement
from app.db.models.operations import (
    Conversation,
    DeletionLedger,
    Job,
    Message,
    ModelRun,
    SyncEvent,
    WeeklyReview,
)
from app.db.models.profile import MemoryCandidate, Profile, ProfileFact, UserState
from app.db.models.training import RecordRevision, SessionExercise, WorkoutSession, WorkoutSet


async def record_deletion(db: AsyncSession, user_id: UUID, scope: dict) -> DeletionLedger:
    """Record what was deleted so restores can re-apply it."""
    ledger = DeletionLedger(
        user_id=user_id,
        scope=scope,
        minimal_identifiers={"user_id": str(user_id), **{k: v for k, v in scope.items() if k != "tables"}},
        completed_at=datetime.now(tz=None),
    )
    db.add(ledger)
    await db.flush()
    return ledger


async def delete_user_data(db: AsyncSession, user_id: UUID) -> dict:
    """Delete all user data across tables; returns per-table counts."""
    counts: dict[str, int] = {}

    async def _delete(model, label: str, *filters):
        result = await db.execute(delete(model).where(model.user_id == user_id, *filters))
        counts[label] = result.rowcount or 0

    # Dependent rows first
    await _delete(WorkoutSet, "workout_sets")
    await _delete(SessionExercise, "session_exercises")
    await _delete(WorkoutSession, "workout_sessions")
    await _delete(RecordRevision, "record_revisions")
    await _delete(Measurement, "measurements")
    await _delete(MealLog, "meal_logs")
    await _delete(PlanVersion, "plan_versions")
    await _delete(ProfileFact, "profile_facts")
    await _delete(MemoryCandidate, "memory_candidates")
    await _delete(Profile, "profiles")
    await _delete(Message, "messages")
    await _delete(Conversation, "conversations")
    await _delete(WeeklyReview, "weekly_reviews")
    await _delete(SyncEvent, "sync_events")

    # Knowledge: own sources cascade revisions/chunks
    own_sources = (
        await db.execute(select(KnowledgeSource.id).where(KnowledgeSource.owner_user_id == user_id))
    ).fetchall()
    if own_sources:
        source_ids = [row[0] for row in own_sources]
        own_revisions = (
            await db.execute(select(SourceRevision.id).where(SourceRevision.source_id.in_(source_ids)))
        ).fetchall()
        if own_revisions:
            revision_ids = [row[0] for row in own_revisions]
            result = await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source_revision_id.in_(revision_ids)))
            counts["knowledge_chunks"] = result.rowcount or 0
            await db.execute(delete(SourceRevision).where(SourceRevision.id.in_(revision_ids)))
        counts["knowledge_sources"] = len(source_ids)
        await db.execute(delete(KnowledgeSource).where(KnowledgeSource.id.in_(source_ids)))

    result = await db.execute(delete(Asset).where(Asset.owner_user_id == user_id))
    counts["assets"] = result.rowcount or 0

    # Model runs and jobs are operational records
    result = await db.execute(delete(ModelRun).where(ModelRun.user_id == user_id))
    counts["model_runs"] = result.rowcount or 0
    await db.execute(delete(Job).where(Job.owner_user_id == user_id))
    await db.delete(await db.get(UserState, user_id))

    await record_deletion(
        db,
        user_id,
        {"tables": sorted(counts.keys()), "reason": "user_delete", "counts": counts},
    )
    await db.commit()
    return counts


async def reap_deletions_after_restore(db: AsyncSession) -> int:
    """After restoring an old backup, re-apply all deletion ledger rows."""
    ledgers = (
        await db.execute(select(DeletionLedger).order_by(DeletionLedger.created_at))
    ).scalars().all()

    reapplied = 0
    seen_users: set[UUID] = set()
    for ledger in ledgers:
        if ledger.user_id in seen_users:
            continue  # latest ledger for a user covers earlier ones
        seen_users.add(ledger.user_id)
        await delete_user_data_strict(db, ledger.user_id)
        reapplied += 1
    await db.commit()
    return reapplied


async def delete_user_data_strict(db: AsyncSession, user_id: UUID) -> None:
    """Delete by user_id only (post-restore re-application)."""
    await delete_user_data(db, user_id)
