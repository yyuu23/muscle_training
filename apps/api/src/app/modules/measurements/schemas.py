"""
Measurement schemas (plan §5.6 / §6.3)
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class MeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    measurement_type: str
    value: Decimal
    unit: str
    observed_at: datetime
    source: str
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class MeasurementListResponse(BaseModel):
    items: list[MeasurementResponse]
    next_cursor: str | None = None
