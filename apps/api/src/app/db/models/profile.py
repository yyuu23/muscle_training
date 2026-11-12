"""
Profile and memory models (plan §5.3)

- profile_facts is the single source of truth for confirmed preferences/limits.
- model_inference can never directly become a confirmed fact.
- Weight is stored in measurements, not as long-term text memory.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

FACT_KINDS = (
    "exercise_preference",
    "exercise_exclusion",
    "equipment_preference",
    "diet_preference",
    "allergy_report",
    "training_limitation",
    "unresolved_discomfort",
)

PROVENANCE_KINDS = (
    "user_statement",
    "reported_professional_advice",
    "reported_third_party",
    "model_inference",
)


class Profile(Base):
    """User training profile"""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Core profile data (units explicit: cm, months, minutes)
    goal: Mapped[str | None] = mapped_column(Text)
    height_cm: Mapped[int | None] = mapped_column(Integer)
    training_experience_months: Mapped[int | None] = mapped_column(Integer)
    sessions_per_week: Mapped[int | None] = mapped_column(Integer)
    minutes_per_session: Mapped[int | None] = mapped_column(Integer)

    # JSONB lists: available_weekdays [1..7] (Mon=1), equipment ["barbell", ...],
    # available_load_increments ["2.5", ...] in kg
    available_weekdays: Mapped[list | None] = mapped_column(JSONB)
    equipment: Mapped[list | None] = mapped_column(JSONB)
    available_load_increments: Mapped[list | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="profile")
    facts: Mapped[list["ProfileFact"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class ProfileFact(Base):
    """Confirmed preference/limitation fact with provenance."""

    __tablename__ = "profile_facts"
    __table_args__ = (
        UniqueConstraint("user_id", "kind", "fact_key", name="uq_profile_fact_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"))

    kind: Mapped[str] = mapped_column(
        Enum(*FACT_KINDS, name="profile_fact_kind"),
        nullable=False,
    )
    fact_key: Mapped[str] = mapped_column(String(200), nullable=False)

    value: Mapped[str] = mapped_column(Text, nullable=False)

    provenance: Mapped[str] = mapped_column(
        Enum(*PROVENANCE_KINDS, name="profile_fact_provenance"),
        nullable=False,
    )
    source_ref: Mapped[str | None] = mapped_column(Text)

    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    superseded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    profile: Mapped["Profile"] = relationship(back_populates="facts")


class MemoryCandidate(Base):
    """Proposed fact awaiting user confirmation."""

    __tablename__ = "memory_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)

    proposed_fact: Mapped[str] = mapped_column(Text, nullable=False)

    source_kind: Mapped[str] = mapped_column(
        Enum(*PROVENANCE_KINDS, name="memory_candidate_source"),
        nullable=False,
    )
    source_ref: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        Enum("pending", "accepted", "rejected", "superseded", name="candidate_status"),
        nullable=False,
        default="pending",
    )

    # proposal metadata: {"kind": ..., "fact_key": ...}
    # (named `meta`: `metadata` is reserved for Declarative MetaData)
    meta: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserState(Base):
    """Planning revision and active plan pointer."""

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
from app.db.models.auth import User  # noqa: E402, F401
