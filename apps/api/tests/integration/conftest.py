"""
Integration test fixtures (plan §12.2).

Requires a real PostgreSQL + pgvector (never SQLite):
    TEST_DATABASE_URL=postgresql+asyncpg://muscle_training:dev_password@localhost:5432/muscle_test

The muscle_test database is created automatically on first use (the
server must be reachable; compose.dev.yml maps localhost:5432 with
superuser muscle_training / dev_password and the bootstrap roles).

Each test gets its own engine: create_all → run → drop_all. This avoids
pytest-asyncio loop-scope mismatches (no session-scoped async fixtures)
and cross-loop connection reuse.

Two schema flavors:
- ``db`` / ``http``: ORM create_all (fast, per-test) — RLS policies are
  NOT present, but table grants are given to app_runtime /
  job_dispatcher so role-based checks still work.
- ``migrated_db_url``: runs alembic upgrade head on a throwaway
  database (full migration chain incl. RLS policies + grants).
"""

import asyncio
import os
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Ensure test env before app imports
os.environ.setdefault("PYTHON_ENV", "test")
os.environ.setdefault("MODEL_PROVIDER", "fake")

API_ROOT = Path(__file__).resolve().parents[2]  # apps/api

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://muscle_training:dev_password@localhost:5432/muscle_test",
)

pytestmark = pytest.mark.integration

# Active-test pointers (set by the db fixture; used by create_invite)
_current_session = None
_current_engine = None


def _url_with_db(url: str, dbname: str) -> str:
    return url.rsplit("/", 1)[0] + "/" + dbname


_test_db_ready = False


def _ensure_test_database() -> None:
    """CREATE DATABASE muscle_test once per process (idempotent)."""
    global _test_db_ready
    if _test_db_ready:
        return

    target = TEST_DATABASE_URL.rsplit("/", 1)[-1]
    maintenance_url = _url_with_db(TEST_DATABASE_URL, "muscle_training_dev")
    # Fall back to the default maintenance DB if the dev one is absent
    # (e.g. a standalone test server).
    candidates = [maintenance_url, _url_with_db(TEST_DATABASE_URL, "postgres")]

    async def _create() -> None:
        last_error: Exception | None = None
        for base in candidates:
            try:
                engine = create_async_engine(base, isolation_level="AUTOCOMMIT")
            except Exception as err:  # noqa: BLE001
                last_error = err
                continue
            try:
                async with engine.connect() as conn:
                    exists = (
                        await conn.execute(
                            text("SELECT 1 FROM pg_database WHERE datname = :d"), {"d": target}
                        )
                    ).scalar()
                    if not exists:
                        await conn.execute(text(f'CREATE DATABASE "{target}"'))
                _test_db_ready = True
                return
            except Exception as err:  # noqa: BLE001
                last_error = err
            finally:
                await engine.dispose()
        raise RuntimeError(f"无法创建测试数据库 {target}（compose.dev.yml 是否已启动？）") from last_error

    asyncio.run(_create())


@pytest_asyncio.fixture
async def db():
    """Per-test engine + schema: create_all → yield session → drop_all."""
    global _current_session, _current_engine
    _ensure_test_database()

    from app.db import models  # noqa: F401 register all models
    from app.db.base import Base

    engine = create_async_engine(TEST_DATABASE_URL, echo=os.environ.get("TEST_SQL_ECHO") == "1")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)
        # create_all tables are owned by the connecting (super)user and
        # carry no RLS; still grant DML to the runtime roles so
        # SET LOCAL ROLE-based tests behave like the migrated schema.
        await conn.execute(
            text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_runtime, job_dispatcher")
        )
        await conn.execute(
            text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_runtime, job_dispatcher")
        )

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        _current_session = session
        _current_engine = engine
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    _current_session = None
    _current_engine = None


@pytest_asyncio.fixture
async def http(db):
    """ASGI client sharing the test session's DB."""
    from app.db.session import get_db_session
    from app.main import app

    async def override():
        yield db

    app.dependency_overrides[get_db_session] = override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _run_alembic(database_url: str, *args: str) -> None:
    """Run alembic in a subprocess against the given database URL."""
    import subprocess
    import sys

    env = dict(os.environ)
    env["DATABASE_URL"] = database_url
    env["MIGRATION_DATABASE_URL"] = database_url
    env["PYTHONPATH"] = str(API_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(API_ROOT / "alembic.ini"), *args],
        cwd=str(API_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"alembic {' '.join(args)} 失败:\n{result.stdout}\n{result.stderr}")


@pytest.fixture
def migrated_db_url():
    """Throwaway database migrated with the full alembic chain
    (includes RLS policies and role grants). Yields its URL; the
    database is dropped afterwards. Superuser connection info is taken
    from TEST_DATABASE_URL."""
    _ensure_test_database()
    dbname = f"muscle_test_mig_{uuid.uuid4().hex[:10]}"
    url = _url_with_db(TEST_DATABASE_URL, dbname)

    maintenance_url = _url_with_db(TEST_DATABASE_URL, "muscle_training_dev")

    async def _create_db() -> None:
        engine = create_async_engine(maintenance_url, isolation_level="AUTOCOMMIT")
        try:
            async with engine.connect() as conn:
                await conn.execute(text(f'CREATE DATABASE "{dbname}"'))
        finally:
            await engine.dispose()

    asyncio.run(_create_db())
    _run_alembic(url, "upgrade", "head")
    try:
        yield url
    finally:
        async def _drop_db() -> None:
            engine = create_async_engine(maintenance_url, isolation_level="AUTOCOMMIT")
            try:
                async with engine.connect() as conn:
                    await conn.execute(
                        text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :d AND pid <> pg_backend_pid()"),
                        {"d": dbname},
                    )
                    await conn.execute(text(f'DROP DATABASE IF EXISTS "{dbname}"'))
            finally:
                await engine.dispose()

        asyncio.run(_drop_db())


async def create_invite() -> str:
    """Create an invite in the active test session (returns the raw code).

    invites.created_by has an FK to users.id, so a real admin user is
    created first. The admin INSERT is flushed and verified visible in
    this transaction BEFORE the invite is added — this both guarantees
    FK ordering and surfaces the real error if the users INSERT fails.
    """
    from sqlalchemy import func, select

    from app.db.models.auth import Invite, User
    from app.utils.auth import calculate_invite_expiry, generate_invite_code, hash_token
    from app.utils.password import hash_password

    assert _current_session is not None, "create_invite() must run inside a test with the db fixture"

    admin = User(
        id=uuid.uuid4(),
        username_normalized=f"admin-{uuid.uuid4().hex[:12]}",
        display_name="测试管理员",
        password_hash=hash_password("admin-password-123"),
        role="admin",
        status="active",
    )
    _current_session.add(admin)
    await _current_session.flush()

    # Sanity check: this admin's row must be visible inside this transaction
    visible = (
        await _current_session.execute(
            select(func.count()).select_from(User).where(User.id == admin.id)
        )
    ).scalar()
    assert visible == 1, f"admin INSERT not visible in transaction (count={visible})"

    code = generate_invite_code()
    _current_session.add(
        Invite(
            code_hash=hash_token(code),
            created_by=admin.id,
            expires_at=calculate_invite_expiry(),
        )
    )
    await _current_session.commit()
    return code


async def register_user(http: AsyncClient, username: str, *, invite_code: str | None = None):
    """Register via invite; returns (user_id, csrf_token, cookies)."""
    if invite_code is None:
        invite_code = await create_invite()

    response = await http.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": "correct-horse-battery",
            "display_name": username,
            "invite_code": invite_code,
        },
        headers={"Origin": "http://test", "Content-Type": "application/json"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    return data["user"]["id"], data["csrf_token"], response.cookies
