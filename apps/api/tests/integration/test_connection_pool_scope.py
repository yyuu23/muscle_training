"""
Connection-pool user scoping (plan §9.3 / §12.2): the RLS user
context is TRANSACTION-local — a mid-request commit drops it, the
after_begin hook re-applies it, and a session never leaks its user to
the next pooled request.
"""

import uuid

import pytest
from sqlalchemy import text

from app.db.scope import set_user_context

pytestmark = pytest.mark.integration


async def _current_user_id(db) -> str | None:
    """Read the transaction-local app.user_id (NULL → None)."""
    value = (
        await db.execute(text("SELECT NULLIF(current_setting('app.user_id', true), '')"))
    ).scalar()
    return value or None


async def test_context_reapplied_after_commit(db):
    user_a = uuid.uuid4()

    await set_user_context(db, user_a)
    assert await _current_user_id(db) == str(user_a)

    # Service code commits mid-request → transaction-local setting dies…
    await db.commit()
    # …but the after_begin hook re-applies it on the next transaction.
    assert await _current_user_id(db) == str(user_a)


async def test_context_switch_does_not_leak(db):
    """Two consecutive "requests" on the same session: the second user
    fully replaces the first; clearing removes it entirely (pool-safe)."""
    user_a, user_b = uuid.uuid4(), uuid.uuid4()

    await set_user_context(db, user_a)
    await db.commit()

    await set_user_context(db, user_b)
    assert await _current_user_id(db) == str(user_b)
    assert await _current_user_id(db) != str(user_a)
    await db.commit()

    # A fresh session (next pooled request) starts with NO context.
    from sqlalchemy.ext.asyncio import async_sessionmaker

    maker = async_sessionmaker(db.get_bind(), expire_on_commit=False)
    async with maker() as other:
        assert await _current_user_id(other) is None

    # …and clearing on the original session denies again.
    await set_user_context(db, None)
    assert await _current_user_id(db) is None
