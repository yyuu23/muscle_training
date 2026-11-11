"""
Test authentication service
"""

import pytest

from app.db.models.auth import User
from app.modules.auth.schemas import LoginRequest, RegisterRequest
from app.modules.auth.service import AuthService


@pytest.mark.asyncio
async def test_register_user_success(db_session):
    """Test successful user registration"""
    service = AuthService(db_session)

    # Create invite first
    admin_user = User(
        username_normalized="admin",
        display_name="Admin",
        password_hash="hash",
        role="admin",
    )
    db_session.add(admin_user)
    await db_session.commit()

    invite = await service.create_invite(admin_user.id, "Test invite")

    # Register user
    request = RegisterRequest(
        invite_code=invite.code,
        username="testuser",
        display_name="Test User",
        password="SecurePassword123!",
    )

    user, session = await service.register_user(request, "127.0.0.1")

    assert user.username_normalized == "testuser"
    assert user.display_name == "Test User"
    assert user.role == "member"
    assert session.token is not None


@pytest.mark.asyncio
async def test_register_with_invalid_invite(db_session):
    """Test registration with invalid invite code"""
    service = AuthService(db_session)

    request = RegisterRequest(
        invite_code="invalid_code",
        username="testuser",
        display_name="Test User",
        password="SecurePassword123!",
    )

    with pytest.raises(ValueError, match="Invalid or expired invite code"):
        await service.register_user(request, "127.0.0.1")


@pytest.mark.asyncio
async def test_login_success(db_session):
    """Test successful login"""
    service = AuthService(db_session)

    # Create and register user first
    admin_user = User(
        username_normalized="admin",
        display_name="Admin",
        password_hash="hash",
        role="admin",
    )
    db_session.add(admin_user)
    await db_session.commit()

    invite = await service.create_invite(admin_user.id)

    register_req = RegisterRequest(
        invite_code=invite.code,
        username="testuser",
        display_name="Test User",
        password="SecurePassword123!",
    )

    await service.register_user(register_req, "127.0.0.1")

    # Now login
    login_req = LoginRequest(
        username="testuser",
        password="SecurePassword123!",
    )

    user, session = await service.login_user(login_req, "127.0.0.1")

    assert user.username_normalized == "testuser"
    assert session.token is not None


@pytest.mark.asyncio
async def test_login_wrong_password(db_session):
    """Test login with wrong password"""
    service = AuthService(db_session)

    # Create and register user first
    admin_user = User(
        username_normalized="admin",
        display_name="Admin",
        password_hash="hash",
        role="admin",
    )
    db_session.add(admin_user)
    await db_session.commit()

    invite = await service.create_invite(admin_user.id)

    register_req = RegisterRequest(
        invite_code=invite.code,
        username="testuser",
        display_name="Test User",
        password="SecurePassword123!",
    )

    await service.register_user(register_req, "127.0.0.1")

    # Try login with wrong password
    login_req = LoginRequest(
        username="testuser",
        password="WrongPassword123!",
    )

    with pytest.raises(ValueError, match="Invalid username or password"):
        await service.login_user(login_req, "127.0.0.1")
