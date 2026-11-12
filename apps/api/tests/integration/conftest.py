"""
Integration test fixtures (plan §12.2).

Requires a real PostgreSQL + pgvector (never SQLite):
    TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/muscle_test

Each test gets its own engine: create_all → run → drop_all. This avoids
pytest-asyncio loop-scope mismatches (no session-scoped async fixtures)
and cross-loop connection reuse.
"""

import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Ensure test env before app imports
os.environ.setdefault("PYTHON_ENV", "test")
os.environ.setdefault("MODEL_PROVIDER", "fake")

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/muscle_test",
)

pytestmark = pytest.mark.integration

# Active-test pointers (set by the db fixture; used by create_invite)
_current_session = None
_current_engine = None


@pytest_asyncio.fixture
async def db():
    """Per-test engine + schema: create_all → yield session → drop_all."""
    global _current_session, _current_engine

    from app.db import models  # noqa: F401 register all models
    from app.db.base import Base

    engine = create_async_engine(TEST_DATABASE_URL, echo=os.environ.get("TEST_SQL_ECHO") == "1")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)

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
