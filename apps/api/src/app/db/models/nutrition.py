"""
Measurement and nutrition models (plan §5.6)

- Values use NUMERIC, API transmits decimal strings.
- Nutrition sources distinguish user labels from model estimates.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

NUTRITION_SOURCES = ("user_label", "user_estimate", "model_estimate", "unknown")


class Measurement(Base):
    """Body measurements. First version opens weight UI only."""

    __tablename__ = "measurements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    measurement_type: Mapped[str] = mapped_column(
        Enum("weight", "body_fat_percentage", "circumference", "other", name="measurement_type"),
        nullable=False,
    )

    value: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)  # kg, cm, %

    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="user_logged")

    notes: Mapped[str | None] = mapped_column(Text)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MealLog(Base):
    """Meal logging with source-tracked nutrition estimates."""

    __tablename__ = "meal_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    meal_type: Mapped[str | None] = mapped_column(
        Enum("breakfast", "lunch", "dinner", "snack", "other", name="meal_type"),
    )

    description: Mapped[str] = mapped_column(Text, nullable=False)

    items: Mapped[list | None] = mapped_column(JSONB)

    # {"calories": ..., "protein_g": ..., ...} with explicit source
    nutrition: Mapped[dict | None] = mapped_column(JSONB)
    nutrition_source: Mapped[str] = mapped_column(
        Enum(*NUTRITION_SOURCES, name="nutrition_source"),
        nullable=False,
        default="unknown",
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
