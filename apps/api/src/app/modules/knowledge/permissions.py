"""
Knowledge permissions (plan §5.7 / §4.2)

- New uploads default to private.
- Sharing to the shared library is an explicit admin action.
- Withdrawn sources stop appearing in new retrievals; historical plans
  keep their content, citations show "来源已删除/已撤回".
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, ErrorCode
from app.db.models.knowledge import KnowledgeSource


async def can_read_source(db: AsyncSession, source: KnowledgeSource, user_id: UUID, *, is_admin: bool = False) -> bool:
    """Shared sources are readable; private only by owner or admin."""
    if source.visibility == "shared":
        return True
    if is_admin:
        return True
    return source.owner_user_id == user_id


async def get_readable_source(
    db: AsyncSession, source_id: UUID, user_id: UUID, *, is_admin: bool = False
) -> KnowledgeSource:
    """Load a source the user may read; 404-style hiding for the rest."""
    source = await db.get(KnowledgeSource, source_id)
    if source is None or not await can_read_source(db, source, user_id, is_admin=is_admin):
        raise ApiError(ErrorCode.NOT_FOUND, "来源不存在")
    return source


async def require_owner(db: AsyncSession, source_id: UUID, user_id: UUID) -> KnowledgeSource:
    """Only the owner (or admin path) can modify/import from a source."""
    source = await db.get(KnowledgeSource, source_id)
    if source is None or source.owner_user_id != user_id:
        raise ApiError(ErrorCode.NOT_FOUND, "来源不存在")
    return source


async def visible_source_ids(db: AsyncSession, user_id: UUID) -> list[UUID]:
    """Ids of sources visible to this user (shared + own)."""
    result = await db.execute(
        select(KnowledgeSource.id).where(
            (KnowledgeSource.visibility == "shared")
            | (KnowledgeSource.owner_user_id == user_id)
        )
    )
    return [row[0] for row in result.fetchall()]
