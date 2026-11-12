"""
Profile schemas (plan §5.3 / §6.2)

- PATCH requires expected_version (optimistic locking).
- Weight belongs to measurements, never to long-term text memory.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FACT_KINDS = Literal[
    "exercise_preference",
    "exercise_exclusion",
    "equipment_preference",
    "diet_preference",
    "allergy_report",
    "training_limitation",
    "unresolved_discomfort",
]

PROVENANCE = Literal[
    "user_statement",
    "reported_professional_advice",
    "reported_third_party",
    "model_inference",
]


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    version: int
    goal: str | None
    height_cm: int | None = Field(None, ge=50, le=300)
    training_experience_months: int | None = Field(None, ge=0, le=720)
    sessions_per_week: int | None = Field(None, ge=0, le=14)
    minutes_per_session: int | None = Field(None, ge=10, le=360)
    available_weekdays: list[int] | None
    equipment: list[str] | None
    available_load_increments: list[str] | None
    created_at: datetime
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    """PATCH /profile with expected_version."""

    expected_version: int = Field(..., ge=1)
    goal: str | None = Field(None, max_length=500)
    height_cm: int | None = Field(None, ge=50, le=300)
    training_experience_months: int | None = Field(None, ge=0, le=720)
    sessions_per_week: int | None = Field(None, ge=0, le=14)
    minutes_per_session: int | None = Field(None, ge=10, le=360)
    available_weekdays: list[int] | None = Field(None)
    equipment: list[str] | None = Field(None, max_length=50)
    available_load_increments: list[str] | None = Field(None, max_length=50)

    @model_validator(mode="after")
    def check_weekdays(self):
        if self.available_weekdays is not None:
            for day in self.available_weekdays:
                if not 1 <= day <= 7:
                    raise ValueError("available_weekdays 取值必须是 1-7（周一=1）")
        if self.available_load_increments is not None:
            for inc in self.available_load_increments:
                try:
                    value = float(inc)
                except ValueError as exc:
                    raise ValueError("重量增量必须是数字字符串") from exc
                if value <= 0 or value > 100:
                    raise ValueError("重量增量必须在 (0, 100] kg 范围内")
        return self


class ProfileFactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    kind: str
    fact_key: str
    value: str
    provenance: str
    source_ref: str | None
    confirmed_at: datetime
    effective_at: datetime
    superseded_by: uuid.UUID | None
    superseded_at: datetime | None
    created_at: datetime


class ProfileFactCreateRequest(BaseModel):
    """Explicit form input becomes a user-confirmed fact directly."""

    kind: FACT_KINDS
    fact_key: str = Field(..., min_length=1, max_length=200)
    value: str = Field(..., min_length=1, max_length=1000)
    source_ref: str | None = Field(None, max_length=500)


class FactSupersedeRequest(BaseModel):
    """Explicitly replace a fact, keeping provenance."""

    value: str = Field(..., min_length=1, max_length=1000)
    source_ref: str | None = Field(None, max_length=500)


class MemoryCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    proposed_fact: str
    source_kind: str
    source_ref: str | None
    status: str
    meta: dict | None
    created_at: datetime
    resolved_at: datetime | None


class MemoryCandidateResolveRequest(BaseModel):
    decision: Literal["accept", "reject"]


class ProfileWithFactsResponse(BaseModel):
    profile: ProfileResponse
    facts: list[ProfileFactResponse]
    planning_revision: int
