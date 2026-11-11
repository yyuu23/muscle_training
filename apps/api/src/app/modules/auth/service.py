"""
Authentication service layer
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import AuthAttempt, AuthSession, Invite, User
from app.db.models.profile import Profile, UserState
from app.modules.auth.schemas import LoginRequest, RegisterRequest
from app.utils.auth import (
    calculate_invite_expiry,
    calculate_session_expiry,
    generate_invite_code,
    generate_session_token,
    normalize_username,
)
from app.utils.password import hash_password, verify_password
from app.utils.validation import validate_display_name, validate_password, validate_username


class AuthService:
    """Authentication business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_rate_limit(self, username: str, ip_address: str, window_minutes: int = 15, max_attempts: int = 5) -> bool:
        """
        Check if authentication attempts are within rate limit

        Args:
            username: Username being attempted
            ip_address: IP address of the attempt
            window_minutes: Time window in minutes
            max_attempts: Maximum attempts allowed

        Returns:
            True if within limit, False if exceeded
        """
        cutoff = datetime.now() - timedelta(minutes=window_minutes)

        result = await self.db.execute(
            select(AuthAttempt)
            .where(AuthAttempt.username_normalized == normalize_username(username))
            .where(AuthAttempt.ip_address == ip_address)
            .where(AuthAttempt.attempted_at > cutoff)
        )

        attempts = result.scalars().all()
        return len(attempts) < max_attempts

    async def record_auth_attempt(self, username: str, ip_address: str, success: bool) -> None:
        """Record an authentication attempt"""
        attempt = AuthAttempt(
            username_normalized=normalize_username(username),
            ip_address=ip_address,
            success=success,
        )
        self.db.add(attempt)
        await self.db.commit()

    async def validate_invite_code(self, code: str) -> Invite | None:
        """
        Validate invite code

        Args:
            code: Invite code to validate

        Returns:
            Invite object if valid, None otherwise
        """
        result = await self.db.execute(
            select(Invite)
            .where(Invite.code == code)
            .where(Invite.used_at.is_(None))
            .where(Invite.expires_at > datetime.now())
        )

        return result.scalar_one_or_none()

    async def register_user(self, request: RegisterRequest, ip_address: str) -> tuple[User, AuthSession]:
        """
        Register a new user

        Args:
            request: Registration request data
            ip_address: IP address of the registration

        Returns:
            Tuple of (User, AuthSession)

        Raises:
            ValueError: If validation fails
        """
        # Validate input
        valid, error = validate_username(request.username)
        if not valid:
            raise ValueError(error)

        valid, error = validate_password(request.password)
        if not valid:
            raise ValueError(error)

        valid, error = validate_display_name(request.display_name)
        if not valid:
            raise ValueError(error)

        # Validate invite code
        invite = await self.validate_invite_code(request.invite_code)
        if not invite:
            raise ValueError("Invalid or expired invite code")

        # Check if username already exists
        username_normalized = normalize_username(request.username)
        result = await self.db.execute(
            select(User).where(User.username_normalized == username_normalized)
        )

        if result.scalar_one_or_none():
            raise ValueError("Username already exists")

        # Create user
        user = User(
            username_normalized=username_normalized,
            display_name=request.display_name,
            password_hash=hash_password(request.password),
            role="member",
            status="active",
        )

        self.db.add(user)
        await self.db.flush()

        # Mark invite as used
        invite.used_by = user.id
        invite.used_at = datetime.now()

        # Create user profile
        profile = Profile(user_id=user.id, version=1)
        self.db.add(profile)

        # Create user state
        user_state = UserState(user_id=user.id, planning_revision=1)
        self.db.add(user_state)

        # Create session
        session = AuthSession(
            user_id=user.id,
            token=generate_session_token(),
            expires_at=calculate_session_expiry(),
            ip_address=ip_address,
        )

        self.db.add(session)
        await self.db.commit()

        return user, session

    async def login_user(self, request: LoginRequest, ip_address: str, user_agent: str | None = None) -> tuple[User, AuthSession]:
        """
        Login a user

        Args:
            request: Login request data
            ip_address: IP address of the login
            user_agent: User agent string

        Returns:
            Tuple of (User, AuthSession)

        Raises:
            ValueError: If credentials are invalid
        """
        username_normalized = normalize_username(request.username)

        # Find user
        result = await self.db.execute(
            select(User)
            .where(User.username_normalized == username_normalized)
            .where(User.status == "active")
        )

        user = result.scalar_one_or_none()

        # Verify password
        if not user or not verify_password(request.password, user.password_hash):
            await self.record_auth_attempt(request.username, ip_address, success=False)
            raise ValueError("Invalid username or password")

        # Create new session
        session = AuthSession(
            user_id=user.id,
            token=generate_session_token(),
            expires_at=calculate_session_expiry(),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.db.add(session)
        await self.record_auth_attempt(request.username, ip_address, success=True)
        await self.db.commit()

        return user, session

    async def logout_user(self, session: AuthSession) -> None:
        """Logout a user by revoking their session"""
        session.revoked = True
        session.revoked_at = datetime.now()
        await self.db.commit()

    async def create_invite(self, created_by: UUID, note: str | None = None) -> Invite:
        """
        Create a new invite code

        Args:
            created_by: User ID creating the invite
            note: Optional note about the invite

        Returns:
            Created invite object
        """
        invite = Invite(
            code=generate_invite_code(),
            created_by=created_by,
            expires_at=calculate_invite_expiry(),
            note=note,
        )

        self.db.add(invite)
        await self.db.commit()

        return invite


from datetime import timedelta  # noqa: E402
