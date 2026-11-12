"""
Conversation schemas (plan §6.4 / §6.5)
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Free chat; explicit business entries bypass this endpoint."""

    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: uuid.UUID | None = None


class CitationOut(BaseModel):
    chunk_id: str
    quote: str | None = None


class CoachResponseOut(BaseModel):
    """Unified agent answer (plan §6.5)."""

    status: str
    answer_markdown: str = ""
    citations: list[CitationOut] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    proposed_actions: list[dict] = Field(default_factory=list)
    data_cutoff_at: str | None = None
    request_id: str | None = None
    draft_id: str | None = None
    plan_draft_id: str | None = None
    memory_candidate_ids: list[str] = Field(default_factory=list)
    conversation_id: uuid.UUID | None = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    evidence_refs: list
    created_at: datetime


class DraftConfirmRequest(BaseModel):
    """Confirm a model-organized record draft; still goes through
    normal business services (plan §6.4)."""

    decision: str = Field(..., pattern="^(accept|reject)$")
    payload: dict | None = None


class DraftConfirmResponse(BaseModel):
    outcome: str
    entity_id: str | None = None
    detail: dict | None = None
