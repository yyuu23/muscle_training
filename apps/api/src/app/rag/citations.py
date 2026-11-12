"""
Citation validation (plan §7.9 / §6.5)

A citation is valid only when it:
- belongs to this retrieval result set,
- comes from a source the user can access,
- references the live (active) revision of that source.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge import KnowledgeChunk, KnowledgeSource, SourceRevision


@dataclass
class CitationCheck:
    cited_id: str
    valid: bool
    reason: str | None = None


def extract_citations(answer: dict) -> list[str]:
    """Pull citation ids from a model answer (citations[] field).

    Accepts plain id strings or {"chunk_id": ...} dicts.
    """
    raw = answer.get("citations") or []
    ids = []
    for c in raw:
        if isinstance(c, dict):
            chunk_id = c.get("chunk_id")
            if chunk_id:
                ids.append(str(chunk_id))
        elif c:
            ids.append(str(c))
    return ids


async def validate_citations(
    db: AsyncSession,
    user_id: UUID,
    retrieved_chunk_ids: list[UUID],
    cited_ids: list[str],
) -> list[CitationCheck]:
    """Validate each citation against the retrieval result + permissions."""
    retrieved = set(retrieved_chunk_ids)
    checks: list[CitationCheck] = []

    for cited in cited_ids:
        try:
            chunk_id = UUID(cited)
        except ValueError:
            checks.append(CitationCheck(cited_id=cited, valid=False, reason="引用 ID 不是合法 UUID"))
            continue

        if chunk_id not in retrieved:
            checks.append(
                CitationCheck(cited_id=cited, valid=False, reason="引用不在本次检索结果中（可能是编造）")
            )
            continue

        chunk = await db.get(KnowledgeChunk, chunk_id)
        if chunk is None:
            checks.append(CitationCheck(cited_id=cited, valid=False, reason="引用片段不存在"))
            continue

        revision = await db.get(SourceRevision, chunk.source_revision_id)
        if revision is None:
            checks.append(CitationCheck(cited_id=cited, valid=False, reason="引用修订不存在"))
            continue

        source = (
            await db.execute(select(KnowledgeSource).where(KnowledgeSource.id == revision.source_id))
        ).scalar_one_or_none()

        if source is None:
            checks.append(CitationCheck(cited_id=cited, valid=False, reason="引用来源不存在"))
            continue

        if source.status in ("withdrawn", "failed"):
            checks.append(CitationCheck(cited_id=cited, valid=False, reason="来源已撤回或失效"))
            continue

        if source.visibility == "private" and source.owner_user_id != user_id:
            checks.append(CitationCheck(cited_id=cited, valid=False, reason="无权访问该私有来源"))
            continue

        if source.active_revision_id != chunk.source_revision_id:
            checks.append(CitationCheck(cited_id=cited, valid=False, reason="引用的不是当前有效版本"))
            continue

        checks.append(CitationCheck(cited_id=cited, valid=True))

    return checks


def citations_pass(checks: list[CitationCheck]) -> bool:
    return all(check.valid for check in checks)
