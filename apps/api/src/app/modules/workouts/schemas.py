"""
Workout session management schemas
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class WorkoutSessionCreateRequest(BaseModel):
    """Create workout session"""

    plan_version_id: UUID | None = None
    plan_day_key: str | None = Field(None, max_length=50)
    started_at: datetime
    precheck: dict | None = None


class WorkoutSessionResponse(BaseModel):
    """Workout session response"""

    id: UUID
    user_id: UUID
    plan_version_id: UUID | None
    plan_day_key: str | None
    started_at: datetime
    completed_at: datetime | None
    status: str
    precheck: dict | None
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SessionExerciseCreateRequest(BaseModel):
    """Add exercise to session"""

    exercise_id: UUID
    plan_item_id: str | None = Field(None, max_length=100)
    ordinal: int = Field(..., ge=0)
    equipment_label: str | None = Field(None, max_length=100)
    override_reason: str | None = None


class SessionExerciseResponse(BaseModel):
    """Session exercise response"""

    id: UUID
    session_id: UUID
    exercise_id: UUID
    plan_item_id: str | None
    ordinal: int
    equipment_label: str | None
    override_reason: str | None
    completion_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class WorkoutSetCreateRequest(BaseModel):
    """Record workout set"""

    set_index: int = Field(..., ge=1)
    set_kind: str = Field(default="work", pattern="^(warmup|work)$")
    status: str = Field(default="completed", pattern="^(planned|completed|failed|skipped)$")
    load_kg: Decimal | None = Field(None, ge=0, decimal_places=2)
    load_mode: str | None = Field(None, pattern="^(total_external|per_implement|bodyweight|assistance|band)$")
    reps: int | None = Field(None, ge=0)
    duration_seconds: int | None = Field(None, ge=0)
    rir: int | None = Field(None, ge=0, le=10)
    discomfort_report: str | None = Field(None, max_length=500)
    performed_at: datetime


class WorkoutSetResponse(BaseModel):
    """Workout set response"""

    id: UUID
    session_exercise_id: UUID
    set_index: int
    set_kind: str
    status: str
    load_kg: Decimal | None
    load_mode: str | None
    reps: int | None
    duration_seconds: int | None
    rir: int | None
    discomfort_report: str | None
    performed_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class CompleteSessionRequest(BaseModel):
    """Complete workout session"""

    completed_at: datetime
