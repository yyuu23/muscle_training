"""
Catalog schemas (plan §6.3 / §10.1 / §10.2)
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExerciseResponse(BaseModel):
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
    approved_alternatives: list
    evidence_refs: list
    review_status: str
    fixture: bool
    created_at: datetime


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    content_version: int
    name: str
    intended_population: str | None
    sessions_per_week: int
    required_intake_fields: list
    eligibility: dict
    session_slots: list
    progression_policy: str
    time_estimation_parameters: dict
    approved_short_session_variants: list
    evidence_refs: list
    review_status: str
    fixture: bool
    created_at: datetime


class ContentValidationIssue(BaseModel):
    code: str
    message: str
    path: str | None = None


class ContentImportRequest(BaseModel):
    """Import content from the content/ directory (admin)."""

    content_root: str = Field(..., max_length=500)
    kind: Literal["exercises", "templates"]


class ContentImportResponse(BaseModel):
    imported: int
    skipped: int
    issues: list[ContentValidationIssue]


class ContentValidateResponse(BaseModel):
    valid: bool
    issues: list[ContentValidationIssue]


class ContentReviewRequest(BaseModel):
    """Approve or reject draft content (admin)."""

    decision: Literal["approve", "reject"]
    note: str | None = Field(None, max_length=500)


class ContentReviewResponse(BaseModel):
    id: uuid.UUID
    slug: str
    content_version: int
    review_status: str
    reviewed_at: datetime | None
