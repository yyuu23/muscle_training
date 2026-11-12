"""
Sync event schemas (plan §8.4 / §8.5)

Six event types. Events carry client-generated entity ids; user
ownership always comes from authentication, never from payload.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

SyncEventType = Literal[
    "workout.started",
    "session_exercise.added",
    "set.logged",
    "workout.completed",
    "measurement.created",
    "meal.created",
]

LoadMode = Literal["total_external", "per_implement", "bodyweight", "assistance", "band"]


class SyncEventPayload(BaseModel):
    """Base: client ids and observed time."""

    id: uuid.UUID
    client_created_at: datetime


class WorkoutStartedPayload(SyncEventPayload):
    plan_version_id: uuid.UUID | None = None
    plan_day_key: str | None = Field(None, max_length=50)
    started_at: datetime
    precheck: dict | None = None


class SessionExerciseAddedPayload(SyncEventPayload):
    session_id: uuid.UUID
    exercise_id: uuid.UUID
    plan_item_id: str | None = Field(None, max_length=100)
    position: int = Field(..., ge=0)
    equipment_label: str | None = Field(None, max_length=100)
    override_reason: str | None = Field(None, max_length=500)


class SetLoggedPayload(SyncEventPayload):
    session_exercise_id: uuid.UUID
    set_index: int = Field(..., ge=1)
    set_kind: Literal["warmup", "work"] = "work"
    status: Literal["completed", "skipped", "failed"] = "completed"
    load_kg: Annotated[Decimal | None, Field(None, ge=0, decimal_places=2)] = None
    load_mode: LoadMode | None = None
    reps: int | None = Field(None, ge=0)
    duration_seconds: int | None = Field(None, ge=0)
    rir: int | None = Field(None, ge=0, le=10)
    discomfort_report: str | None = Field(None, max_length=500)
    performed_at: datetime


class WorkoutCompletedPayload(BaseModel):
    """Completes an existing session — carries no new entity id."""

    session_id: uuid.UUID
    completed_at: datetime
    notes: str | None = Field(None, max_length=2000)
    client_created_at: datetime


class MeasurementCreatedPayload(SyncEventPayload):
    measurement_type: Literal["weight", "body_fat_percentage", "circumference", "other"] = "weight"
    value: Decimal = Field(..., gt=0, decimal_places=2)
    unit: str = Field(..., max_length=20)
    observed_at: datetime
    notes: str | None = Field(None, max_length=500)


class MealCreatedPayload(SyncEventPayload):
    occurred_at: datetime
    meal_type: Literal["breakfast", "lunch", "dinner", "snack", "other"] | None = None
    description: str = Field(..., min_length=1, max_length=2000)
    items: list | None = None
    nutrition: dict | None = None
    nutrition_source: Literal["user_label", "user_estimate", "model_estimate", "unknown"] = "unknown"


class SyncEventItem(BaseModel):
    """One event from the device outbox."""

    event_id: uuid.UUID
    device_id: uuid.UUID
    client_sequence: int = Field(..., ge=0)
    event_type: SyncEventType
    client_created_at: datetime
    payload: dict


class SyncEventResult(BaseModel):
    """Per-item result (plan §8.5)."""

    event_id: uuid.UUID
    outcome: Literal["applied", "already_applied", "dependency_pending", "rejected"]
    detail: dict | None = None
    retryable: bool = True


class SyncBatchRequest(BaseModel):
    events: list[SyncEventItem] = Field(..., min_length=1, max_length=100)


class SyncBatchResponse(BaseModel):
    results: list[SyncEventResult]


class SnapshotPlan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence_number: int
    status: str
    content: dict
    activated_at: datetime | None


class SnapshotProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: int
    goal: str | None
    height_cm: int | None
    training_experience_months: int | None
    sessions_per_week: int | None
    minutes_per_session: int | None
    available_weekdays: list | None
    equipment: list | None
    available_load_increments: list | None


class SnapshotFact(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    fact_key: str
    value: str
    provenance: str


class SnapshotExercise(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    content_version: int
    name: str
    aliases: list
    movement_pattern: str | None
    equipment_tags: list
    metric_type: str
    load_mode: str
    instructions: list
    common_errors: list


class SyncSnapshotResponse(BaseModel):
    """Snapshot for offline cache refresh (plan §8.6)."""

    generated_at: datetime
    planning_revision: int
    profile: SnapshotProfile | None
    facts: list[SnapshotFact]
    active_plan: SnapshotPlan | None
    exercises: list[SnapshotExercise]
    recent_sessions: list[dict]
    recent_measurements: list[dict]
    recent_meals: list[dict]
