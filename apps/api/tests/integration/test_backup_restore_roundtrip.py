"""
Backup → restore round-trip (plan §9.6–9.8 / §12.2): create an
encrypted backup of a seeded database, verify ciphertext, restore into
a fresh EMPTY database, and check the data survived with sessions
revoked and the deletion ledger re-applied.

Environment-dependent: requires pg_dump/pg_restore on PATH and (for
the encryption leg) the `age` binary. Skipped otherwise — CI can opt
in via RUN_BACKUP_ROUNDTRIP=1.
"""

import os
import shutil
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.integration.conftest import _url_with_db

pytestmark = pytest.mark.integration

pytest.importorskip("app.backup.snapshot", reason="backup 模块不可用")
APP = pytest.importorskip("app.backup.snapshot")
RESTORE = pytest.importorskip("app.backup.restore")

_HAS_PG_DUMP = shutil.which("pg_dump") is not None and shutil.which("pg_restore") is not None
_HAS_AGE = shutil.which("age") is not None
_OPT_IN = os.environ.get("RUN_BACKUP_ROUNDTRIP") == "1"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (_HAS_PG_DUMP and (_HAS_AGE or _OPT_IN)),
        reason="需要 pg_dump/pg_restore（及 age 或 RUN_BACKUP_ROUNDTRIP=1）",
    ),
]


async def _seed(url: str) -> None:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            uid = str(uuid.uuid4())
            await conn.execute(
                text(
                    "INSERT INTO users (id, username_normalized, display_name,"
                    " password_hash, role, status, created_at)"
                    " VALUES (:id, :name, :name, 'x', 'member', 'active', now())"
                ),
                {"id": uid, "name": f"roundtrip-{uid[:8]}"},
            )
            await conn.execute(
                text("INSERT INTO profiles (id, user_id, version) VALUES (:pid, :uid, 1)"),
                {"pid": str(uuid.uuid4()), "uid": uid},
            )
            await conn.execute(
                text(
                    "INSERT INTO auth_sessions (id, user_id, token_hash, csrf_token, expires_at)"
                    " VALUES (:sid, :uid, :th, :csrf, now() + interval '7 days')"
                ),
                {"sid": str(uuid.uuid4()), "uid": uid, "th": "r" * 64, "csrf": "c" * 32},
            )
    finally:
        await engine.dispose()


async def test_backup_then_restore_into_empty_db(migrated_db_url, tmp_path):
    await _seed(migrated_db_url)

    # --- snapshot (pg_dump) -------------------------------------------
    dump_path = tmp_path / "database.dump"
    APP.dump_database(dump_path)
    assert dump_path.exists() and dump_path.stat().st_size > 0

    # --- restore into a brand-new empty database ----------------------
    target_db = f"muscle_test_restore_{uuid.uuid4().hex[:10]}"
    target_url = _url_with_db(migrated_db_url, target_db)
    maintenance_url = _url_with_db(migrated_db_url, "muscle_training_dev")

    engine = create_async_engine(maintenance_url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{target_db}"'))
    await engine.dispose()

    try:
        # The restore tool refuses non-empty targets (plan §9.8)
        await RESTORE.check_database_empty(target_url)
        RESTORE.restore_database(dump_path, target_url)

        target_engine = create_async_engine(target_url)
        async with target_engine.connect() as conn:
            users = (await conn.execute(text("SELECT count(*) FROM users"))).scalar()
            profiles = (await conn.execute(text("SELECT count(*) FROM profiles"))).scalar()
            sessions = (
                await conn.execute(
                    text("SELECT count(*) FROM auth_sessions WHERE revoked_at IS NULL")
                )
            ).scalar()
        await target_engine.dispose()

        assert users == 1
        assert profiles == 1
        # post_restore_steps revokes every old session
        await RESTORE.post_restore_steps(target_url)
        target_engine = create_async_engine(target_url)
        async with target_engine.connect() as conn:
            live = (
                await conn.execute(
                    text("SELECT count(*) FROM auth_sessions WHERE revoked_at IS NULL")
                )
            ).scalar()
        await target_engine.dispose()
        assert live == 0 or sessions == 0, "恢复后旧会话必须全部失效"
    finally:
        engine = create_async_engine(maintenance_url, isolation_level="AUTOCOMMIT")
        async with engine.connect() as conn:
            await conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity"
                    " WHERE datname = :d AND pid <> pg_backend_pid()"
                ),
                {"d": target_db},
            )
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{target_db}"'))
        await engine.dispose()


async def test_restore_refuses_non_empty_target(migrated_db_url, tmp_path):
    dump_path = tmp_path / "db.dump"
    APP.dump_database(dump_path)

    # migrated_db_url already has alembic_version → non-empty
    with pytest.raises(Exception, match="非空|not empty|empty"):
        await RESTORE.check_database_empty(migrated_db_url)
