"""
User profile and memory models
"""

import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Profile(Base):
    """User training profile"""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Core profile data
    goal: Mapped[str | None] = mapped_column(Text)
    height_cm: Mapped[int | None] = mapped_column(Integer)
    training_experience: Mapped[str | None] = mapped_column(
        Enum("beginner", "intermediate", "advanced", name="training_experience")
    )
    sessions_per_week: Mapped[int | None] = mapped_column(Integer)

    # Equipment and constraints (JSONB for flexibility)
    available_equipment: Mapped[dict | None] = mapped_column(JSONB)
    time_constraints: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="profile")
    facts: Mapped[list["ProfileFact"]] = relationship(back_populates="profile", cascade="all, delete-orphan")


class ProfileFact(Base):
    """Confirmed user facts with provenance"""

    __tablename__ = "profile_facts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"))

    kind: Mapped[str] = mapped_column(
        Enum(
            "exercise_preference",
            "exclusion",
            "allergy_report",
            "training_limitation",
            "unresolved_discomfort",
            name="profile_fact_kind"
        ),
        nullable=False
    )

    source: Mapped[str] = mapped_column(
        Enum("user_statement", "reported_professional_advice", "model_inference", name="profile_fact_source"),
        nullable=False
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(
        Enum("confirmed", "probable", "unverified", name="confidence_level"),
        nullable=False,
        default="confirmed"
    )

    status: Mapped[str] = mapped_column(
        Enum("active", "superseded", "archived", name="fact_status"),
        nullable=False,
        default="active"
    )

    superseded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    metadata: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    profile: Mapped["Profile"] = relationship(back_populates="facts")


class MemoryCandidate(Base):
    """Memory candidates awaiting user confirmation"""

    __tablename__ = "memory_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))

    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    source: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)

    status: Mapped[str] = mapped_column(
        Enum("pending", "accepted", "rejected", "superseded", name="candidate_status"),
        nullable=False,
        default="pending"
    )

    metadata: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserState(Base):
    """User planning and active state"""

    __tablename__ = "user_state"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    planning_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    active_plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# Import User to resolve relationship
from app.db.models.auth import User  # noqa: E402
