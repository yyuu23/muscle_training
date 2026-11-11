"""
Nutrition and measurement models
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Measurement(Base):
    """Body measurements and metrics"""

    __tablename__ = "measurements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    type: Mapped[str] = mapped_column(
        Enum("weight", "body_fat_percentage", "circumference", "other", name="measurement_type"),
        nullable=False
    )

    value: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)  # kg, cm, %

    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    source: Mapped[str] = mapped_column(
        Enum("user_logged", "device_sync", "estimate", name="measurement_source"),
        nullable=False,
        default="user_logged"
    )

    notes: Mapped[str | None] = mapped_column(Text)
    metadata: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MealLog(Base):
    """Meal and nutrition logging"""

    __tablename__ = "meal_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    meal_type: Mapped[str | None] = mapped_column(
        Enum("breakfast", "lunch", "dinner", "snack", "other", name="meal_type")
    )

    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Structured items (optional)
    items: Mapped[list | None] = mapped_column(JSONB)

    # Nutrition data with source tracking
    nutrition: Mapped[dict | None] = mapped_column(JSONB)  # {"calories": 500, "protein": 30, "source": "user_estimate"}

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
