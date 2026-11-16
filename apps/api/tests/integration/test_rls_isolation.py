"""
Row-level security isolation (plan §9.3 / §12.2): as the
least-privilege app_runtime role, users only ever see their own rows;
a missing user context denies everything; owner-scoped tables expose
shared/system rows but guard writes.

Runs against a fully migrated throwaway database (real policies from
migration b2r3l4s5c7d8, not ORM create_all). The connecting user is a
superuser; tests drop to app_runtime with SET LOCAL ROLE so policies
actually apply (superusers bypass RLS).
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = pytest.mark.integration


async def _seed_two_users(url: str) -> tuple[str, str]:
    """Create two users + one profile each as superuser; returns ids."""
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            a, b = str(uuid.uuid4()), str(uuid.uuid4())
            for uid in (a, b):
                await conn.execute(
                    text(
                        "INSERT INTO users (id, username_normalized, display_name,"
                        " password_hash, role, status, timezone, created_at)"
                        " VALUES (:id, :name, :name, 'x', 'member', 'active',"
                        " 'Asia/Shanghai', now())"
                    ),
                    {"id": uid, "name": f"u-{uid[:8]}"},
                )
                await conn.execute(
                    text("INSERT INTO profiles (id, user_id, version) VALUES (:id, :uid, 1)"),
                    {"id": str(uuid.uuid4()), "uid": uid},
                )
                await conn.execute(
                    text(
                        "INSERT INTO measurements (id, user_id, measurement_type, value,"
                        " unit, observed_at, source, version)"
                        " VALUES (:id, :uid, 'weight', 70, 'kg', now(), 'user_logged', 1)"
                    ),
                    {"id": str(uuid.uuid4()), "uid": uid},
                )
            return a, b
    finally:
        await engine.dispose()


async def _as_app_runtime(url: str, sql: str, ctx: str | None):
    """Run one statement as app_runtime with an optional user context.
    Returns all rows."""
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            async with conn.begin():
                await conn.execute(text("SET LOCAL ROLE app_runtime"))
                if ctx is not None:
                    await conn.execute(
                        text("SELECT set_config('app.user_id', :v, true)"), {"v": ctx}
                    )
                result = await conn.execute(text(sql))
                return result.fetchall()
    finally:
        await engine.dispose()


async def test_users_only_see_own_rows(migrated_db_url):
    user_a, user_b = await _seed_two_users(migrated_db_url)

    rows = await _as_app_runtime(
        migrated_db_url, "SELECT user_id FROM profiles", ctx=user_a
    )
    assert {str(r[0]) for r in rows} == {user_a}

    rows = await _as_app_runtime(
        migrated_db_url, "SELECT user_id FROM measurements", ctx=user_b
    )
    assert {str(r[0]) for r in rows} == {user_b}


async def test_missing_context_denies_everything(migrated_db_url):
    user_a, _ = await _seed_two_users(migrated_db_url)

    rows = await _as_app_runtime(migrated_db_url, "SELECT user_id FROM profiles", ctx=None)
    assert rows == []
    # Empty-string context (explicitly cleared) denies too.
    rows = await _as_app_runtime(migrated_db_url, "SELECT 1 FROM profiles LIMIT 1", ctx="")
    assert rows == []


async def test_write_requires_matching_context(migrated_db_url):
    user_a, user_b = await _seed_two_users(migrated_db_url)

    # Inserting rows for another user must fail the WITH CHECK clause.
    engine = create_async_engine(migrated_db_url)
    try:
        async with engine.connect() as conn:
            async with conn.begin():
                await conn.execute(text("SET LOCAL ROLE app_runtime"))
                await conn.execute(
                    text("SELECT set_config('app.user_id', :v, true)"), {"v": user_a}
                )
                with pytest.raises(Exception, match="row-level security|RLS"):
                    await conn.execute(
                        text(
                            "INSERT INTO measurements (id, user_id, measurement_type, value,"
                            " unit, observed_at, source, version)"
                            " VALUES (:id, :uid, 'weight', 80, 'kg', now(), 'user_logged', 1)"
                        ),
                        {"id": str(uuid.uuid4()), "uid": user_b},
                    )
    finally:
        await engine.dispose()


async def test_owner_tables_shared_read_private_write(migrated_db_url):
    user_a, _ = await _seed_two_users(migrated_db_url)

    # System-owned row (owner IS NULL) is readable without any context.
    engine = create_async_engine(migrated_db_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO jobs (id, owner_user_id, type, status, payload, attempts,"
                    " max_attempts, run_after)"
                    " VALUES (:id, NULL, 'maintenance', 'queued', '{}', 0, 3, now())"
                ),
                {"id": str(uuid.uuid4())},
            )
            await conn.execute(
                text(
                    "INSERT INTO knowledge_sources (id, owner_user_id, visibility, title,"
                    " source_type, status)"
                    " VALUES (:id, NULL, 'shared', '共享资料', 'document', 'ready')"
                ),
                {"id": str(uuid.uuid4())},
            )
    finally:
        await engine.dispose()

    rows = await _as_app_runtime(migrated_db_url, "SELECT title FROM knowledge_sources", ctx=None)
    assert [r[0] for r in rows] == ["共享资料"]  # shared/system readable

    rows = await _as_app_runtime(migrated_db_url, "SELECT count(*) FROM jobs", ctx=None)
    assert rows[0][0] == 1  # system job visible
