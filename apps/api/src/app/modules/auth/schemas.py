"""
Auth schemas (plan §6.2)
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.utils.validation import validate_display_name, validate_password, validate_username


class RegisterRequest(BaseModel):
    """Register with invite code"""

    username: str = Field(..., max_length=50)
    password: str = Field(..., max_length=128)
    display_name: str = Field(..., max_length=100)
    invite_code: str = Field(..., min_length=8, max_length=64)

    @model_validator(mode="after")
    def validate_fields(self):
        for ok, err in (
            validate_username(self.username),
            validate_password(self.password),
            validate_display_name(self.display_name),
        ):
            if not ok and err:
                raise ValueError(err)
        return self


class LoginRequest(BaseModel):
    """Login with username and password"""

    username: str = Field(..., max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    # ORM column is username_normalized; the API contract exposes `username`
    username: str = Field(validation_alias="username_normalized")
    display_name: str
    role: str
    timezone: str
    status: str
    created_at: datetime


class CapabilitiesResponse(BaseModel):
    """Model/content/storage availability; never includes secrets."""

    model_config = ConfigDict(from_attributes=True)

    chat_model_configured: bool
    embedding_model_configured: bool
    transcription_configured: bool
    content_ready: bool
    storage_configured: bool
    offline_recording_available: bool = True


class AuthMeResponse(BaseModel):
    user: UserResponse
    csrf_token: str
    capabilities: CapabilitiesResponse


class SessionTokenResponse(BaseModel):
    """Response for login/register; the session token itself only travels in cookie."""

    user: UserResponse
    csrf_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=12, max_length=128)

    @model_validator(mode="after")
    def validate_new_password(self):
        ok, err = validate_password(self.new_password)
        if not ok and err:
            raise ValueError(err)
        return self


class ResetPasswordRequest(BaseModel):
    """Reset with one-time token created by admin CLI."""

    token: str = Field(..., min_length=16, max_length=128)
    new_password: str = Field(..., min_length=12, max_length=128)

    @model_validator(mode="after")
    def validate_new_password(self):
        ok, err = validate_password(self.new_password)
        if not ok and err:
            raise ValueError(err)
        return self


class InviteCreateRequest(BaseModel):
    note: str | None = Field(None, max_length=200)


class InviteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_by: uuid.UUID
    expires_at: datetime
    used_by: uuid.UUID | None = None
    used_at: datetime | None = None
    note: str | None = None
    created_at: datetime


class InviteCreatedResponse(BaseModel):
    """Admin-only response that reveals the raw code exactly once."""

    invite: InviteResponse
    code: str
