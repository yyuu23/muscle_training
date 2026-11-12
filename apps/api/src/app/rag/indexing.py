"""
Indexing pipeline (plan §7.9 / §7.10)

- Vector generation with model version verification.
- Query and document vectors must share model + dimension.
- Re-embedding creates a new index revision; the switch is atomic:
  the source's active_revision_id flips only after indexing completes.
"""

import logging
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge import KnowledgeChunk, KnowledgeSource, SourceRevision
from app.providers import get_embedding_provider
from app.providers.interfaces import EmbeddingRequest
from app.rag.chunking import chunk_document, chunk_transcript

logger = logging.getLogger(__name__)


async def index_revision(
    db: AsyncSession,
    revision_id: UUID,
    *,
    segments: list[dict] | None = None,
    document_text: str | None = None,
    annotations: list[dict] | None = None,
) -> int:
    """Chunk and embed a revision's content.

    Returns the number of chunks indexed. Chunks are written for this
    revision only; other revisions keep their own chunks, so the switch
    is atomic at revision granularity.
    """
    if segments is not None:
        chunks = chunk_transcript(segments)
    elif document_text is not None:
        chunks = chunk_document(document_text, annotations=annotations)
    else:
        raise ValueError("segments 或 document_text 必须提供其一")

    provider = get_embedding_provider()
    model_name = getattr(provider, "model", "fake-embedding")

    # Embed all chunk texts in batches
    texts = [c.text for c in chunks]
    vectors: list[list[float]] = []
    for start in range(0, len(texts), 25):
        batch = texts[start : start + 25]
        result = await provider.embed(EmbeddingRequest(texts=batch, purpose="indexing"))
        vectors.extend(result.vectors)

    # Replace any previous chunks for this revision (retry-safe reindex)
    existing = (
        await db.execute(select(KnowledgeChunk).where(KnowledgeChunk.source_revision_id == revision_id))
    ).scalars().all()
    for chunk_row in existing:
        await db.delete(chunk_row)

    for chunk, vector in zip(chunks, vectors, strict=True):
        db.add(
            KnowledgeChunk(
                source_revision_id=revision_id,
                ordinal=chunk.ordinal,
                start_ms=chunk.start_ms,
                end_ms=chunk.end_ms,
                original_text=chunk.text,
                corrected_text=None,
                tags=chunk.tags,
                embedding=vector,
                embedding_model=model_name,
                embedding_dimensions=len(vector),
                content_hash=chunk.content_hash,
            )
        )

    await db.flush()
    return len(chunks)


async def activate_revision(
    db: AsyncSession,
    source_id: UUID,
    revision_id: UUID,
) -> None:
    """Atomically flip the source to the indexed revision and mark ready."""
    revision = await db.get(SourceRevision, revision_id)
    if revision is None:
        raise ValueError("revision 不存在")

    revision.status = "ready"
    await db.execute(
        update(KnowledgeSource)
        .where(KnowledgeSource.id == source_id)
        .values(active_revision_id=revision_id, status="ready")
    )
    await db.commit()


async def verify_model_consistency(db: AsyncSession) -> str | None:
    """Return an error message when stored embeddings mix models."""
    provider = get_embedding_provider()
    model_name = getattr(provider, "model", "fake-embedding")

    rows = (
        await db.execute(
            select(KnowledgeChunk.embedding_model).where(KnowledgeChunk.embedding.isnot(None)).distinct()
        )
    ).fetchall()
    models = {row[0] for row in rows}
    models.discard(None)
    if models and models != {model_name}:
        return (
            f"索引中存在旧向量模型 {models - {model_name}}；"
            "更换向量模型必须重建索引后再切换，不能混用"
        )
    return None
