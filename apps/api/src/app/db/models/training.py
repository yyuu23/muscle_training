"""
Training record models
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkoutSession(Base):
    """Training session"""

    __tablename__ = "workout_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    plan_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    plan_day_key: Mapped[str | None] = mapped_column(String(50))  # e.g., "day_1", "upper_a"

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[str] = mapped_column(
        Enum("in_progress", "completed", "abandoned", name="session_status"),
        nullable=False,
        default="in_progress"
    )

    precheck: Mapped[dict | None] = mapped_column(JSONB)  # Pre-training notes

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SessionExercise(Base):
    """Exercise within a session"""

    __tablename__ = "session_exercises"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workout_sessions.id", ondelete="CASCADE"), nullable=False
    )

    exercise_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    plan_item_id: Mapped[str | None] = mapped_column(String(100))  # Reference to plan structure

    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)  # Order in session

    equipment_label: Mapped[str | None] = mapped_column(String(100))
    override_reason: Mapped[str | None] = mapped_column(Text)

    completion_status: Mapped[str] = mapped_column(
        Enum("not_started", "in_progress", "completed", "skipped", name="exercise_status"),
        nullable=False,
        default="not_started"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WorkoutSet(Base):
    """Individual set record"""

    __tablename__ = "workout_sets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("session_exercises.id", ondelete="CASCADE"), nullable=False
    )

    set_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-based

    set_kind: Mapped[str] = mapped_column(
        Enum("warmup", "work", name="set_kind"),
        nullable=False,
        default="work"
    )

    status: Mapped[str] = mapped_column(
        Enum("planned", "completed", "failed", "skipped", name="set_status"),
        nullable=False,
        default="planned"
    )

    # Load data
    load_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    load_mode: Mapped[str | None] = mapped_column(
        Enum("total_external", "per_implement", "bodyweight", "assistance", "band", name="set_load_mode")
    )

    # Performance data
    reps: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    rir: Mapped[int | None] = mapped_column(Integer)  # Reps in reserve

    discomfort_report: Mapped[str | None] = mapped_column(Text)

    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecordRevision(Base):
    """Audit trail for training record corrections"""

    __tablename__ = "record_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    record_type: Mapped[str] = mapped_column(String(50), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    field: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)

    reason: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
