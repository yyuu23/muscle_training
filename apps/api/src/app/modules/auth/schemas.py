"""
Authentication schemas (Pydantic models for API)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    """User registration request"""

    invite_code: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=3, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=12, max_length=128)

    @field_validator("username")
    @classmethod
    def username_must_be_normalized(cls, v: str) -> str:
        """Normalize username"""
        return v.lower().strip()


class LoginRequest(BaseModel):
    """User login request"""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """Login response with session token"""

    token: str
    user: "UserResponse"
    expires_at: datetime


class UserResponse(BaseModel):
    """User information response"""

    id: UUID
    username: str
    display_name: str
    role: str
    timezone: str
    created_at: datetime

    class Config:
        from_attributes = True


class CreateInviteRequest(BaseModel):
    """Create invite code request"""

    note: str | None = None


class InviteResponse(BaseModel):
    """Invite code response"""

    id: UUID
    code: str
    expires_at: datetime
    used_at: datetime | None
    note: str | None
    created_at: datetime

    class Config:
        from_attributes = True
