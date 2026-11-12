"""
Catalog models: exercises, templates, plan versions (plan §5.4)

Published exercises and templates use immutable content versions.
Plan content JSONB is the single plan body, validated by PlanContent.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

LOAD_MODES = ("total_external", "per_implement", "bodyweight", "assistance", "band")
METRIC_TYPES = ("reps", "duration")


class Exercise(Base):
    """Exercise catalog - immutable versioned content."""

    __tablename__ = "exercises"
    __table_args__ = (
        UniqueConstraint("slug", "content_version", name="uq_exercise_slug_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    content_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    aliases: Mapped[list] = mapped_column(JSONB, default=list)

    movement_pattern: Mapped[str | None] = mapped_column(String(50))
    equipment_tags: Mapped[list] = mapped_column(JSONB, default=list)

    metric_type: Mapped[str] = mapped_column(
        Enum(*METRIC_TYPES, name="exercise_metric_type"),
        nullable=False,
        default="reps",
    )
    load_mode: Mapped[str] = mapped_column(
        Enum(*LOAD_MODES, name="exercise_load_mode"),
        nullable=False,
    )

    instructions: Mapped[list] = mapped_column(JSONB, default=list)
    common_errors: Mapped[list] = mapped_column(JSONB, default=list)
    approved_alternatives: Mapped[list] = mapped_column(JSONB, default=list)  # list of slugs

    evidence_refs: Mapped[list] = mapped_column(JSONB, default=list)

    review_status: Mapped[str] = mapped_column(
        Enum("draft", "approved", "rejected", name="content_review_status"),
        nullable=False,
        default="draft",
        index=True,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    fixture: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TrainingTemplate(Base):
    """Training program template - immutable versioned content."""

    __tablename__ = "training_templates"
    __table_args__ = (
        UniqueConstraint("slug", "content_version", name="uq_template_slug_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    content_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    intended_population: Mapped[str | None] = mapped_column(Text)

    sessions_per_week: Mapped[int] = mapped_column(Integer, nullable=False)

    required_intake_fields: Mapped[list] = mapped_column(JSONB, default=list)
    eligibility: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Full prescription structure: session_slots[] with per-slot set/rep/rest ranges
    session_slots: Mapped[list] = mapped_column(JSONB, default=list)
    allowed_exercise_ids: Mapped[list] = mapped_column(JSONB, default=list)

    allowed_set_ranges: Mapped[dict] = mapped_column(JSONB, default=dict)
    allowed_rep_ranges: Mapped[dict] = mapped_column(JSONB, default=dict)
    allowed_rest_ranges: Mapped[dict] = mapped_column(JSONB, default=dict)
    target_rir_ranges: Mapped[dict] = mapped_column(JSONB, default=dict)

    progression_policy: Mapped[str] = mapped_column(String(100), nullable=False, default="hold")

    time_estimation_parameters: Mapped[dict] = mapped_column(JSONB, default=dict)
    approved_short_session_variants: Mapped[list] = mapped_column(JSONB, default=list)

    evidence_refs: Mapped[list] = mapped_column(JSONB, default=list)

    review_status: Mapped[str] = mapped_column(
        Enum("draft", "approved", "rejected", name="content_review_status"),
        nullable=False,
        default="draft",
        index=True,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    fixture: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlanVersion(Base):
    """Training plan version. Content JSONB is the single plan body."""

    __tablename__ = "plan_versions"
    __table_args__ = (
        UniqueConstraint("user_id", "sequence_number", name="uq_plan_user_sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[str] = mapped_column(
        Enum("draft", "active", "superseded", "archived", name="plan_status"),
        nullable=False,
        default="draft",
        index=True,
    )

    content: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Basis versions recorded at generation time (plan §5.9)
    basis_profile_version: Mapped[int | None] = mapped_column(Integer)
    basis_planning_revision: Mapped[int | None] = mapped_column(Integer)
    basis_active_plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    template_versions: Mapped[list | None] = mapped_column(JSONB)  # [{"template_id": ..., "content_version": ...}]

    model_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Optional human/machine rationale summary, citations live inside content
    rationale: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
