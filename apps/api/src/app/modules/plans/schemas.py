"""
Plan schemas (plan §5.4)

PlanContent is the single plan body. Rep-based and duration-based
targets are mutually exclusive; unknown initial load stays null with a
calibration note.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PlanWarmupStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(..., min_length=1, max_length=300)
    duration_seconds: int | None = Field(None, ge=10, le=1800)


class PlanExerciseItem(BaseModel):
    """One exercise inside a plan day."""

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(..., min_length=1, max_length=100)
    exercise_id: uuid.UUID
    exercise_content_version: int = Field(..., ge=1)
    exercise_snapshot: dict = Field(default_factory=dict)

    working_sets: int = Field(..., ge=1, le=20)
    reps_min: int | None = Field(None, ge=0, le=100)
    reps_max: int | None = Field(None, ge=0, le=100)
    duration_seconds: int | None = Field(None, ge=5, le=3600)
    rest_seconds: int = Field(..., ge=15, le=600)
    target_rir: int | None = Field(None, ge=0, le=10)

    # Unknown initial load is null + calibration instruction
    initial_load_kg: str | None = Field(None, pattern=r"^\d+(\.\d{1,2})?$")
    load_instruction: str | None = Field(None, max_length=500)

    approved_alternatives: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_exclusive_targets(self):
        has_reps = self.reps_min is not None or self.reps_max is not None
        has_duration = self.duration_seconds is not None
        if has_reps and has_duration:
            raise ValueError("次数型和时长型目标互斥，不能同时填写")
        if not has_reps and not has_duration:
            raise ValueError("必须填写次数范围或时长之一")
        if has_reps:
            if self.reps_min is None or self.reps_max is None:
                raise ValueError("次数范围必须同时给出最小值和最大值")
            if self.reps_min > self.reps_max:
                raise ValueError("次数范围最小值不能大于最大值")
        return self


class PlanCompletionQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1, max_length=300)


class PlanDay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day_key: str = Field(..., min_length=1, max_length=50)
    weekday: int = Field(..., ge=1, le=7)  # 1=Monday
    estimated_minutes: int = Field(..., ge=10, le=240)
    warmup_steps: list[PlanWarmupStep] = Field(default_factory=list)
    exercises: list[PlanExerciseItem] = Field(..., min_length=1)
    completion_questions: list[PlanCompletionQuestion] = Field(default_factory=list)


class PlanContent(BaseModel):
    """Validated plan body stored as plan_versions.content."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=200)
    goal: str = Field(..., min_length=1, max_length=500)
    timezone: str = Field(..., max_length=50)

    days: list[PlanDay] = Field(..., min_length=1)
    notes: str | None = Field(None, max_length=2000)
    evidence_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_day_keys(self):
        keys = [d.day_key for d in self.days]
        if len(keys) != len(set(keys)):
            raise ValueError("day_key 不能重复")
        return self


class PlanVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    sequence_number: int
    status: str
    content: dict
    basis_profile_version: int | None
    basis_planning_revision: int | None
    basis_active_plan_id: uuid.UUID | None
    template_versions: list | None
    model_run_id: uuid.UUID | None
    rationale: str | None
    created_at: datetime
    activated_at: datetime | None
    superseded_at: datetime | None


class PlanListResponse(BaseModel):
    items: list[PlanVersionResponse]
    next_cursor: str | None = None


class PlanActiveResponse(BaseModel):
    plan: PlanVersionResponse | None = None


class PlanActivateRequest(BaseModel):
    """Explicit user adoption; the model can never activate directly."""

    expected_basis_planning_revision: int = Field(..., ge=1)


class PlanActivateResponse(BaseModel):
    plan: PlanVersionResponse
    superseded_plan_id: uuid.UUID | None = None


class PlanValidationIssue(BaseModel):
    code: str
    message: str
    item_id: str | None = None


class PlanDetailResponse(BaseModel):
    plan: PlanVersionResponse
    validation_issues: list[PlanValidationIssue]
    diff_vs_active: dict | None = None
