"""
Reviews schemas
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WeeklyReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    week_start: datetime
    data_revision: int
    data_cutoff_at: datetime
    statistics: dict
    narrative: str | None
    proposed_plan_id: uuid.UUID | None
    stale: bool
    model_run_id: uuid.UUID | None
    created_at: datetime


class WeeklyReviewListResponse(BaseModel):
    items: list[WeeklyReviewResponse]
    next_cursor: str | None = None


class WeeklyReviewCreateRequest(BaseModel):
    week_start: datetime | None = None
