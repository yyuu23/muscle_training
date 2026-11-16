"""
Authenticated user scoping for row-level security (plan §9.3).

The active user id is stored on the AsyncSession (``session.info``) and
applied as a TRANSACTION-LOCAL ``app.user_id`` setting at every
transaction begin (``set_config(..., is_local => true)``). Because the
setting is transaction-scoped:

- it never leaks to the next request that borrows the pooled connection
  (§9.3 forbids connection-level settings);
- service code may commit mid-request and the value is re-applied
  automatically on the next begin within the same session.

RLS policies (migration b2r3l4s5c7d8) treat an unset value as deny.
"""

from uuid import UUID

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session

USER_CTX_KEY = "app_user_id"


async def set_user_context(session: AsyncSession, user_id: UUID | None) -> None:
    """Bind the session to a user (None clears). Takes effect for the
    current transaction and is re-applied on every future begin."""
    if user_id is None:
        session.info.pop(USER_CTX_KEY, None)
        await session.execute(text("SELECT set_config('app.user_id', '', true)"))
        return
    session.info[USER_CTX_KEY] = str(user_id)
    await session.execute(
        text("SELECT set_config('app.user_id', :uid, true)"), {"uid": str(user_id)}
    )


def install_user_context_hook(session_maker: async_sessionmaker) -> None:
    """Re-apply the user context whenever a transaction begins on a
    session produced by ``session_maker`` (handles mid-request commits
    and pooled-connection switches).

    ``after_begin`` is a sync-Session ORM event; AsyncSession delegates
    to its underlying ``Session`` (``session.info`` is shared between
    them), so we listen on the sync class. Installed once at import of
    ``app.db.session``.
    """

    @event.listens_for(Session, "after_begin")
    def _apply_user_context(session, transaction, connection):  # noqa: ARG001
        uid = session.info.get(USER_CTX_KEY)
        if uid:
            connection.execute(
                text("SELECT set_config('app.user_id', :uid, true)"), {"uid": uid}
            )
