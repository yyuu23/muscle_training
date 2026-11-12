"""
Auth + CSRF integration tests (plan §9.2 / §12.2): invite registration
with cookie session, CSRF enforcement, logout, cross-user 404.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.training import WorkoutSession
from tests.integration.conftest import create_invite, register_user

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_register_login_logout_flow(http):
    invite = await create_invite()
    user_id, csrf, cookies = await register_user(http, f"flow-{uuid.uuid4().hex[:8]}", invite_code=invite)

    assert csrf  # CSRF token returned on register
    assert "session" in cookies or "__Host-session" in cookies

    me = await http.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["id"] == user_id

    logout = await http.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 204

    me_after = await http.get("/api/v1/auth/me")
    assert me_after.status_code == 401


@pytest.mark.asyncio
async def test_register_with_invalid_invite_rejected(http):
    """Invalid invite codes are rejected with a validation error."""
    response = await http.post(
        "/api/v1/auth/register",
        json={
            "username": f"bad-{uuid.uuid4().hex[:8]}",
            "password": "correct-horse-battery",
            "display_name": "x",
            "invite_code": "definitely-not-an-invite",
        },
        headers={"Origin": "http://test", "Content-Type": "application/json"},
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "邀请码" in error["message"]


@pytest.mark.asyncio
async def test_write_without_csrf_rejected(http):
    await register_user(http, f"csrf-{uuid.uuid4().hex[:8]}")

    response = await http.post(
        "/api/v1/sync/events",
        json={"events": []},
        # missing X-CSRF-Token
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_login_wrong_password_uniform_error(http):
    username = f"login-{uuid.uuid4().hex[:8]}"
    invite = await create_invite()
    await register_user(http, username, invite_code=invite)

    response = await http.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "wrong-password-xxx"},
        headers={"Origin": "http://test", "Content-Type": "application/json"},
    )
    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "AUTH_REQUIRED"
    # Uniform message that doesn't reveal which part was wrong
    assert "用户名或密码错误" in error["message"]


@pytest.mark.asyncio
async def test_cross_user_access_returns_404(http, db: AsyncSession):
    """Accessing another user's private entity surfaces as 404, not 403."""
    owner_id, _, _ = await register_user(http, f"owner-{uuid.uuid4().hex[:8]}")

    session = WorkoutSession(
        id=uuid.uuid4(),
        user_id=uuid.UUID(owner_id),
        started_at=datetime.now(UTC),
        status="in_progress",
        version=1,
    )
    db.add(session)
    await db.commit()

    # A SECOND user (the httpx cookie jar now authenticates as the intruder)
    await register_user(http, f"intruder-{uuid.uuid4().hex[:8]}")

    response = await http.get(f"/api/v1/workouts/sessions/{session.id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_openapi_contains_key_paths():
    from app.main import app

    schema = app.openapi()
    paths = schema["paths"]
    for expected in (
        "/api/v1/auth/login",
        "/api/v1/sync/events",
        "/api/v1/sync/snapshot",
        "/api/v1/plans/active",
        "/api/v1/workouts/sessions",
    ):
        assert expected in paths, f"missing {expected}"
