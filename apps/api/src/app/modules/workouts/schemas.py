"""
Workout module schemas (plan §5.5 / §6.3)

- Numeric loads transmit as decimal strings.
- Unknown reps/load/RIR stay null.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LOAD_MODES = Literal["total_external", "per_implement", "bodyweight", "assistance", "band"]


class WorkoutSessionCreateRequest(BaseModel):
    """Create workout session (used by sync handler workout.started)"""

    id: uuid.UUID
    plan_version_id: uuid.UUID | None = None
    plan_day_key: str | None = Field(None, max_length=50)
    started_at: datetime
    precheck: dict | None = None
    client_created_at: datetime | None = None


class WorkoutSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    plan_version_id: uuid.UUID | None
    plan_day_key: str | None
    started_at: datetime
    completed_at: datetime | None
    status: str
    precheck: dict | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class WorkoutSessionListResponse(BaseModel):
    items: list[WorkoutSessionResponse]
    next_cursor: str | None = None


class WorkoutSessionPatchRequest(BaseModel):
    """Online correction of session metadata (plan §6.3)"""

    expected_version: int = Field(..., ge=1)
    notes: str | None = Field(None, max_length=2000)
    status: Literal["in_progress", "completed", "abandoned"] | None = None
    reason: str = Field(..., min_length=1, max_length=500)


class SessionExerciseCreateRequest(BaseModel):
    """Add exercise to session"""

    id: uuid.UUID
    exercise_id: uuid.UUID
    plan_item_id: str | None = Field(None, max_length=100)
    position: int = Field(..., ge=0)
    equipment_label: str | None = Field(None, max_length=100)
    override_reason: str | None = Field(None, max_length=500)


class SessionExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    session_id: uuid.UUID
    exercise_id: uuid.UUID
    plan_item_id: str | None
    position: int
    equipment_label: str | None
    override_reason: str | None
    completion_status: str
    version: int
    created_at: datetime


class WorkoutSetCreateRequest(BaseModel):
    """Record a set (sync handler set.logged)"""

    id: uuid.UUID
    session_exercise_id: uuid.UUID
    set_index: int = Field(..., ge=1)
    set_kind: Literal["warmup", "work"] = "work"
    status: Literal["completed", "skipped", "failed"] = "completed"
    load_kg: Decimal | None = Field(None, ge=0, decimal_places=2)
    load_mode: LOAD_MODES | None = None
    reps: int | None = Field(None, ge=0)
    duration_seconds: int | None = Field(None, ge=0)
    rir: int | None = Field(None, ge=0, le=10)
    discomfort_report: str | None = Field(None, max_length=500)
    performed_at: datetime


class WorkoutSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    session_exercise_id: uuid.UUID
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
    version: int
    created_at: datetime


class WorkoutSetPatchRequest(BaseModel):
    """Online correction of a recorded set"""

    expected_version: int = Field(..., ge=1)
    load_kg: Decimal | None = Field(None, ge=0, decimal_places=2)
    load_mode: LOAD_MODES | None = None
    reps: int | None = Field(None, ge=0)
    duration_seconds: int | None = Field(None, ge=0)
    rir: int | None = Field(None, ge=0, le=10)
    status: Literal["completed", "skipped", "failed"] | None = None
    reason: str = Field(..., min_length=1, max_length=500)

    @model_validator(mode="after")
    def check_load_reps_compatible(self):
        # skipped must not fake zero reps (plan §5.5)
        if self.status == "skipped" and (self.reps == 0 or self.duration_seconds == 0):
            raise ValueError("skipped 组不能伪造为完成 0 次")
        return self


class CompleteSessionRequest(BaseModel):
    """Complete workout session (sync handler workout.completed)"""

    completed_at: datetime
    notes: str | None = Field(None, max_length=2000)


class SessionDetailResponse(BaseModel):
    """Session with nested exercises and sets (plan §6.3 GET /workout-sessions/{id})"""

    session: WorkoutSessionResponse
    exercises: list[SessionExerciseResponse]
    sets: list[WorkoutSetResponse]
