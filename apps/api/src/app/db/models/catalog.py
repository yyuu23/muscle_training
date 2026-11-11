"""
Exercise and training template catalog models
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Exercise(Base):
    """Exercise catalog - immutable versioned content"""

    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    aliases: Mapped[list] = mapped_column(JSONB, default=list)  # Chinese + English names

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    movement_pattern: Mapped[str | None] = mapped_column(
        Enum("squat", "hinge", "push", "pull", "carry", "rotation", "isolation", name="movement_pattern")
    )

    equipment: Mapped[list] = mapped_column(JSONB, default=list)  # ["barbell", "dumbbell", "bodyweight"]

    metric_type: Mapped[str] = mapped_column(
        Enum("reps", "duration", "distance", name="metric_type"),
        nullable=False,
        default="reps"
    )

    load_mode: Mapped[str] = mapped_column(
        Enum(
            "total_external",
            "per_implement",
            "bodyweight",
            "assistance",
            "band",
            name="load_mode"
        ),
        nullable=False
    )

    instructions: Mapped[str | None] = mapped_column(Text)
    alternatives: Mapped[list] = mapped_column(JSONB, default=list)  # Alternative exercise IDs

    evidence_refs: Mapped[list] = mapped_column(JSONB, default=list)  # Knowledge chunk IDs

    review_status: Mapped[str] = mapped_column(
        Enum("pending_review", "approved", "rejected", name="review_status"),
        nullable=False,
        default="pending_review"
    )

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    fixture: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TrainingTemplate(Base):
    """Training program template"""

    __tablename__ = "training_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    sessions_per_week: Mapped[int] = mapped_column(Integer, nullable=False)

    # Eligibility criteria
    eligibility: Mapped[dict] = mapped_column(JSONB)  # {"experience": ["beginner", "intermediate"], ...}

    # Prescription structure
    prescription: Mapped[dict] = mapped_column(JSONB)  # Full template structure

    # Progression rules reference
    progression_rules: Mapped[str | None] = mapped_column(String(100))  # e.g., "double_progression_v1"

    evidence_refs: Mapped[list] = mapped_column(JSONB, default=list)

    review_status: Mapped[str] = mapped_column(
        Enum("pending_review", "approved", "rejected", name="template_review_status"),
        nullable=False,
        default="pending_review"
    )

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    fixture: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PlanVersion(Base):
    """Training plan version"""

    __tablename__ = "plan_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    sequence: Mapped[int] = mapped_column(Integer, nullable=False)  # Version number for this user

    status: Mapped[str] = mapped_column(
        Enum("draft", "active", "superseded", "archived", name="plan_status"),
        nullable=False,
        default="draft"
    )

    # Plan content (full structure as JSONB)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Rationale and basis
    rationale: Mapped[str | None] = mapped_column(Text)
    basis_profile_version: Mapped[int | None] = mapped_column(Integer)
    basis_template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    basis_template_version: Mapped[int | None] = mapped_column(Integer)

    # Model run tracking
    model_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    adopted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # Optimistic locking
