"""
Hybrid retrieval (plan §7.9)

1. Filter by user permission and publication status (ready sources).
2. Alias-normalize; jieba tokens with PostgreSQL 'simple' text search.
3. Keyword recall 20; exact cosine vector recall 20.
4. RRF fusion k=60, near-duplicate removal, top 6 into model context.

Query and document vectors must share model + dimensions.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge import KnowledgeChunk, KnowledgeSource, SourceRevision
from app.providers import get_embedding_provider
from app.rag.fusion import dedupe_chunks, jaccard_similarity, rrf_fuse
from app.rag.normalization import normalize_query

KEYWORD_RECALL = 20
VECTOR_RECALL = 20
FINAL_CONTEXT = 6


@dataclass
class RetrievedChunk:
    chunk_id: UUID
    source_id: UUID | None
    revision_id: UUID
    ordinal: int
    start_ms: int | None
    end_ms: int | None
    display_text: str
    title: str
    original_url: str | None
    rrf_score: float
    sources: list[str]


async def _visible_revision_ids(db: AsyncSession, user_id: UUID) -> list[UUID]:
    """Ready shared sources + the user's own ready private sources."""
    query = (
        select(SourceRevision.id)
        .join(KnowledgeSource, SourceRevision.source_id == KnowledgeSource.id)
        .where(KnowledgeSource.status == "ready")
        .where(
            (KnowledgeSource.visibility == "shared")
            | (KnowledgeSource.owner_user_id == user_id)
        )
    )
    rows = (await db.execute(query)).fetchall()
    return [row[0] for row in rows]


async def _load_chunks_ordered(db: AsyncSession, chunk_ids: list[UUID]) -> list[KnowledgeChunk]:
    if not chunk_ids:
        return []
    chunks = (
        await db.execute(select(KnowledgeChunk).where(KnowledgeChunk.id.in_(chunk_ids)))
    ).scalars().all()
    order = {cid: idx for idx, cid in enumerate(chunk_ids)}
    return sorted(chunks, key=lambda c: order.get(c.id, 999))


async def keyword_recall(
    db: AsyncSession, user_id: UUID, query: str, *, limit: int = KEYWORD_RECALL
) -> list[KnowledgeChunk]:
    """jieba-tokenized keyword search over visible ready chunks."""
    normalized = normalize_query(query)
    tokens = normalized["tokens"]
    if not tokens:
        return []

    revision_ids = await _visible_revision_ids(db, user_id)
    if not revision_ids:
        return []

    # OR across tokens; ranking by number of matching tokens (fallback: id)
    match_exprs = []
    params: dict = {"limit": limit}
    for i, token in enumerate(tokens[:8]):
        match_exprs.append(
            f"(to_tsvector('simple', coalesce(corrected_text, original_text)) "
            f"@@ plainto_tsquery('simple', :t{i}))"
        )
        params[f"t{i}"] = token
    match_sql = " OR ".join(match_exprs)

    sql = sql_text(
        f"""
        SELECT id FROM knowledge_chunks
        WHERE source_revision_id = ANY(:revision_ids)
          AND ({match_sql})
        LIMIT :limit
        """
    )
    params["revision_ids"] = revision_ids

    try:
        result = await db.execute(sql, params)
        chunk_ids = [row[0] for row in result.fetchall()]
    except Exception:
        chunk_ids = []

    return await _load_chunks_ordered(db, chunk_ids)


async def vector_recall(
    db: AsyncSession,
    user_id: UUID,
    query: str,
    *,
    limit: int = VECTOR_RECALL,
) -> list[KnowledgeChunk]:
    """Exact cosine vector search over visible ready chunks."""
    from app.providers.interfaces import EmbeddingRequest

    provider = get_embedding_provider()
    result = await provider.embed(EmbeddingRequest(texts=[query], purpose="query"))
    embedding = result.vectors[0]

    revision_ids = await _visible_revision_ids(db, user_id)
    if not revision_ids:
        return []

    vector_literal = "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"
    sql = sql_text(
        """
        SELECT id FROM knowledge_chunks
        WHERE source_revision_id = ANY(:revision_ids)
          AND embedding IS NOT NULL
          AND embedding_model = :model
        ORDER BY embedding <=> :vector
        LIMIT :limit
        """
    )
    try:
        result = await db.execute(
            sql,
            {
                "revision_ids": revision_ids,
                "model": getattr(provider, "model", "fake-embedding"),
                "vector": vector_literal,
                "limit": limit,
            },
        )
        chunk_ids = [row[0] for row in result.fetchall()]
    except Exception:
        chunk_ids = []

    return await _load_chunks_ordered(db, chunk_ids)


async def hybrid_search(
    db: AsyncSession,
    user_id: UUID,
    query: str,
    *,
    final_limit: int = FINAL_CONTEXT,
) -> list[RetrievedChunk]:
    """Permission-filtered hybrid retrieval with RRF fusion."""
    keyword_chunks = await keyword_recall(db, user_id, query)
    vector_chunks = await vector_recall(db, user_id, query)

    rankings = {
        "keyword": [str(c.id) for c in keyword_chunks],
        "vector": [str(c.id) for c in vector_chunks],
    }
    fused = rrf_fuse(rankings)

    texts = {
        str(c.id): (c.corrected_text or c.original_text)
        for c in list(keyword_chunks) + list(vector_chunks)
    }
    fused = dedupe_chunks(fused, lambda cid: texts.get(cid), similarity=jaccard_similarity)
    fused = fused[:final_limit]
    if not fused:
        return []

    chunk_ids = [UUID(f.chunk_id) for f in fused]
    chunks = {c.id: c for c in await _load_chunks_ordered(db, chunk_ids)}

    revisions = {
        r.id: r
        for r in (
            await db.execute(
                select(SourceRevision).where(
                    SourceRevision.id.in_([c.source_revision_id for c in chunks.values()])
                )
            )
        ).scalars().all()
    }
    sources = {
        s.id: s
        for s in (
            await db.execute(
                select(KnowledgeSource).where(
                    KnowledgeSource.id.in_([r.source_id for r in revisions.values()])
                )
            )
        ).scalars().all()
    }

    results: list[RetrievedChunk] = []
    for item in fused:
        chunk = chunks.get(UUID(item.chunk_id))
        if chunk is None:
            continue
        revision = revisions.get(chunk.source_revision_id)
        source = sources.get(revision.source_id) if revision else None
        results.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                source_id=source.id if source else None,
                revision_id=chunk.source_revision_id,
                ordinal=chunk.ordinal,
                start_ms=chunk.start_ms,
                end_ms=chunk.end_ms,
                display_text=chunk.corrected_text or chunk.original_text,
                title=source.title if source else "未知来源",
                original_url=source.original_url if source else None,
                rrf_score=item.rrf_score,
                sources=item.sources,
            )
        )
    return results
