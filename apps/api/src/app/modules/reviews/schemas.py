"""
Reviews schemas
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WeeklySessionDetail(BaseModel):
    session_id: str
    started_at: datetime
    status: str
    duration_minutes: float
    total_working_sets: int
    total_working_reps: int


class WeeklyStatistics(BaseModel):
    """Deterministic weekly statistics (reviews/builder.py is the writer)."""

    week_start: datetime
    week_end: datetime
    data_cutoff_at: datetime
    sessions_completed: int
    sessions_total: int
    planned_days: int | None
    total_working_sets: int
    total_working_reps: int
    skipped_exercises: int
    discomfort_reports: list[str]
    weight_count: int
    weight_first: float | None
    weight_last: float | None
    data_sufficient: bool
    session_details: list[WeeklySessionDetail]


class WeeklyReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    week_start: datetime
    data_revision: int
    data_cutoff_at: datetime
    statistics: WeeklyStatistics
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
