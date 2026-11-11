"""
Profile management schemas
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProfileResponse(BaseModel):
    """User profile response"""

    id: UUID
    user_id: UUID
    version: int
    goal: str | None
    height_cm: int | None
    training_experience: str | None
    sessions_per_week: int | None
    available_equipment: dict | None
    time_constraints: dict | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfileUpdateRequest(BaseModel):
    """Update user profile"""

    goal: str | None = Field(None, max_length=1000)
    height_cm: int | None = Field(None, ge=100, le=250)
    training_experience: str | None = Field(None, pattern="^(beginner|intermediate|advanced)$")
    sessions_per_week: int | None = Field(None, ge=1, le=7)
    available_equipment: dict | None = None
    time_constraints: dict | None = None


class ProfileFactResponse(BaseModel):
    """Profile fact response"""

    id: UUID
    user_id: UUID
    profile_id: UUID
    kind: str
    source: str
    content: str
    confidence: str
    status: str
    metadata: dict | None
    created_at: datetime

    class Config:
        from_attributes = True


class ProfileFactCreateRequest(BaseModel):
    """Create profile fact"""

    kind: str = Field(..., pattern="^(exercise_preference|exclusion|allergy_report|training_limitation|unresolved_discomfort)$")
    source: str = Field(..., pattern="^(user_statement|reported_professional_advice|model_inference)$")
    content: str = Field(..., min_length=1, max_length=2000)
    confidence: str = Field(default="confirmed", pattern="^(confirmed|probable|unverified)$")
    metadata: dict | None = None
