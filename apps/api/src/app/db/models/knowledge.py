"""
Knowledge base models (plan §5.7)

- New uploads default to private; sharing to the shared library is a separate admin action.
- Assets store object keys, never temporary signed URLs.
- Source status: processing / awaiting_review / indexing / ready / failed / withdrawn.
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

SOURCE_STATUSES = ("processing", "awaiting_review", "indexing", "ready", "failed", "withdrawn")
REVISION_STATUSES = ("awaiting_review", "approved", "indexing", "ready", "failed")
RETENTION_CLASSES = ("durable", "temporary_import", "export")


class KnowledgeSource(Base):
    """Knowledge source (video, audio, document, subtitle)."""

    __tablename__ = "knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)

    visibility: Mapped[str] = mapped_column(
        Enum("private", "shared", name="source_visibility"),
        nullable=False,
        default="private",
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str | None] = mapped_column(String(200))
    original_url: Mapped[str | None] = mapped_column(Text)

    source_type: Mapped[str] = mapped_column(
        Enum("video", "audio", "document", "subtitle", name="source_type"),
        nullable=False,
    )

    active_revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    status: Mapped[str] = mapped_column(
        Enum(*SOURCE_STATUSES, name="source_status"),
        nullable=False,
        default="processing",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SourceRevision(Base):
    """Immutable source revision; editing creates a new revision."""

    __tablename__ = "source_revisions"
    __table_args__ = (
        UniqueConstraint("source_id", "revision", name="uq_source_revision_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_sources.id", ondelete="CASCADE")
    )

    revision: Mapped[int] = mapped_column(Integer, nullable=False)

    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    transcript_asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Pre-index content: {"segments": [...]} or {"document_text": "..."}
    content_payload: Mapped[dict | None] = mapped_column(JSONB)

    status: Mapped[str] = mapped_column(
        Enum(*REVISION_STATUSES, name="source_revision_status"),
        nullable=False,
        default="awaiting_review",
    )

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KnowledgeChunk(Base):
    """Knowledge chunk with keyword and vector search support."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_revisions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)

    # Millisecond integer timestamps (plan §7.9)
    start_ms: Mapped[int | None] = mapped_column(Integer)
    end_ms: Mapped[int | None] = mapped_column(Integer)

    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_text: Mapped[str | None] = mapped_column(Text)

    tags: Mapped[list] = mapped_column(JSONB, default=list)

    search_vector: Mapped[list | None] = mapped_column(TSVECTOR)

    embedding: Mapped[list | None] = mapped_column(Vector(1024))
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer)

    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Asset(Base):
    """Stored file asset addressed by object key."""

    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)

    object_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)

    retention_class: Mapped[str] = mapped_column(
        Enum(*RETENTION_CLASSES, name="retention_class"),
        nullable=False,
        default="durable",
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "verified", "expired", "deleted", name="asset_status"),
        nullable=False,
        default="pending",
    )

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
