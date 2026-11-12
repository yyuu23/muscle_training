"""
Nutrition schemas (plan §5.6 / §6.3)
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MealLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    occurred_at: datetime
    meal_type: str | None
    description: str
    items: list | None
    nutrition: dict | None
    nutrition_source: str
    version: int
    created_at: datetime
    updated_at: datetime


class MealLogListResponse(BaseModel):
    items: list[MealLogResponse]
    next_cursor: str | None = None


class MealLogPatchRequest(BaseModel):
    """Online correction of a meal log."""

    expected_version: int = Field(..., ge=1)
    description: str | None = Field(None, min_length=1, max_length=2000)
    meal_type: Literal["breakfast", "lunch", "dinner", "snack", "other"] | None = None
    nutrition: dict | None = None
    nutrition_source: Literal["user_label", "user_estimate", "model_estimate", "unknown"] | None = None
    reason: str = Field(..., min_length=1, max_length=500)
