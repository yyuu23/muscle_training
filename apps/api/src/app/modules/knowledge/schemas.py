"""
Knowledge module schemas (plan §6.4 / §5.7)
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UploadCreateRequest(BaseModel):
    """Create a restricted upload (plan §6.4 POST /assets/uploads)."""

    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., max_length=100)
    byte_size: int = Field(..., gt=0, le=600 * 1024 * 1024)


class UploadCreateResponse(BaseModel):
    asset_id: uuid.UUID
    upload: dict  # {url, method, headers, expires_at, max_size_bytes}
    object_key: str


class UploadCompleteRequest(BaseModel):
    sha256: str = Field(..., min_length=64, max_length=64, pattern="^[0-9a-f]{64}$")


class UploadCompleteResponse(BaseModel):
    asset_id: uuid.UUID
    verified: bool
    byte_size: int | None = None
    detail: str | None = None


class KnowledgeImportRequest(BaseModel):
    """Create an import job from one of my assets (plan §6.4)."""

    asset_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=500)
    author: str | None = Field(None, max_length=200)
    original_url: str | None = Field(None, max_length=2000)


class KnowledgeImportResponse(BaseModel):
    job_id: uuid.UUID
    source_id: uuid.UUID


class KnowledgeSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_user_id: uuid.UUID | None
    visibility: str
    title: str
    author: str | None
    original_url: str | None
    source_type: str
    active_revision_id: uuid.UUID | None
    status: str
    created_at: datetime
    updated_at: datetime


class SourceListResponse(BaseModel):
    items: list[KnowledgeSourceResponse]
    next_cursor: str | None = None


class SourceRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    revision: int
    content_hash: str
    status: str
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    created_at: datetime


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ordinal: int
    start_ms: int | None
    end_ms: int | None
    original_text: str
    corrected_text: str | None
    tags: list


class SourceDetailResponse(BaseModel):
    source: KnowledgeSourceResponse
    revisions: list[SourceRevisionResponse]
    chunks: list[ChunkResponse]


class RevisionPatchRequest(BaseModel):
    """Edit not-yet-published subtitle text/description (plan §6.4)."""

    corrected_chunks: list[dict] = Field(..., max_length=500)


class ShareRequest(BaseModel):
    """Admin publishes a source to the shared library (plan §6.4)."""

    confirm: bool = True


class SourceImportPreview(BaseModel):
    source_id: uuid.UUID
    job_status: str
    phase: str | None
    chunk_count: int | None
