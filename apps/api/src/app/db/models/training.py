"""
Training record models (plan §5.5)

- Every private entity carries user_id.
- Modifiable records carry version (optimistic locking).
- Unknown reps/load/RIR stay null; skipped never fakes zero reps.
- Same exercise under different equipment/load modes is not directly comparable.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

LOAD_MODES = ("total_external", "per_implement", "bodyweight", "assistance", "band")


class WorkoutSession(Base):
    """Training session"""

    __tablename__ = "workout_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    plan_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    plan_day_key: Mapped[str | None] = mapped_column(String(50))

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[str] = mapped_column(
        Enum("in_progress", "completed", "abandoned", name="session_status"),
        nullable=False,
        default="in_progress",
        index=True,
    )

    precheck: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SessionExercise(Base):
    """Exercise within a session"""

    __tablename__ = "session_exercises"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workout_sessions.id", ondelete="CASCADE"), nullable=False
    )

    exercise_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    plan_item_id: Mapped[str | None] = mapped_column(String(100))

    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    equipment_label: Mapped[str | None] = mapped_column(String(100))
    override_reason: Mapped[str | None] = mapped_column(Text)

    completion_status: Mapped[str] = mapped_column(
        Enum("not_recorded", "partial", "completed", "skipped", name="exercise_completion_status"),
        nullable=False,
        default="not_recorded",
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WorkoutSet(Base):
    """Individual set record"""

    __tablename__ = "workout_sets"
    __table_args__ = (
        UniqueConstraint("session_exercise_id", "set_index", name="uq_set_index_per_exercise"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    session_exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("session_exercises.id", ondelete="CASCADE"), nullable=False
    )

    set_index: Mapped[int] = mapped_column(Integer, nullable=False)

    set_kind: Mapped[str] = mapped_column(
        Enum("warmup", "work", name="set_kind"),
        nullable=False,
        default="work",
    )

    status: Mapped[str] = mapped_column(
        Enum("completed", "skipped", "failed", name="set_status"),
        nullable=False,
        default="completed",
    )

    # Load data (kg, NUMERIC transmitted as decimal string)
    load_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    load_mode: Mapped[str | None] = mapped_column(
        Enum(*LOAD_MODES, name="set_load_mode"),
    )

    # Performance data - unknown stays null
    reps: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    rir: Mapped[int | None] = mapped_column(Integer)

    discomfort_report: Mapped[str | None] = mapped_column(Text)

    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecordRevision(Base):
    """Audit trail for record corrections."""

    __tablename__ = "record_revisions"
    __table_args__ = (
        Index("ix_record_revisions_entity", "user_id", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    previous_version: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_value: Mapped[dict | None] = mapped_column(JSONB)
    changed_fields: Mapped[list] = mapped_column(JSONB, default=list)
    reason: Mapped[str | None] = mapped_column(Text)

    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
