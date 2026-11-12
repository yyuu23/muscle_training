"""
Authentication service (plan §9.2)

- Opaque server-side sessions; only SHA-256 token hashes stored.
- Registration and invite consumption happen in one transaction.
- Login failures use a uniform error that does not reveal username existence.
"""

import hashlib
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import (
    AuthAttempt,
    AuthSession,
    Invite,
    PasswordResetToken,
    User,
)
from app.db.models.profile import Profile, UserState
from app.modules.auth.schemas import LoginRequest, RegisterRequest
from app.utils.auth import (
    calculate_invite_expiry,
    calculate_password_reset_expiry,
    calculate_session_expiry,
    generate_csrf_token,
    generate_invite_code,
    generate_password_reset_token,
    generate_session_token,
    hash_token,
    normalize_username,
)
from app.utils.password import hash_password, verify_password
from app.utils.validation import validate_display_name, validate_password, validate_username


class AuthService:
    """Authentication business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    async def check_rate_limit(
        self,
        username: str,
        ip_address: str,
        window_minutes: int = 15,
        max_attempts: int = 5,
    ) -> bool:
        """True if within the allowed attempt count."""
        cutoff = datetime.now(tz=None) - timedelta(minutes=window_minutes)
        username_hash = hashlib.sha256(normalize_username(username).encode()).hexdigest()

        result = await self.db.execute(
            select(AuthAttempt)
            .where(AuthAttempt.username_hash == username_hash)
            .where(AuthAttempt.ip_address == ip_address)
            .where(AuthAttempt.attempted_at > cutoff)
            .where(AuthAttempt.success.is_(False))
        )
        attempts = result.scalars().all()
        return len(attempts) < max_attempts

    async def record_auth_attempt(self, username: str, ip_address: str, success: bool) -> None:
        username_hash = hashlib.sha256(normalize_username(username).encode()).hexdigest()
        self.db.add(
            AuthAttempt(
                username_hash=username_hash,
                ip_address=ip_address,
                success=success,
            )
        )

    # ------------------------------------------------------------------
    # Invites
    # ------------------------------------------------------------------

    async def _get_valid_invite(self, code_hash: str) -> Invite | None:
        result = await self.db.execute(
            select(Invite)
            .where(Invite.code_hash == code_hash)
            .where(Invite.used_at.is_(None))
            .where(Invite.expires_at > datetime.now(tz=None))
        )
        return result.scalar_one_or_none()

    async def create_invite(self, created_by: UUID, note: str | None = None) -> tuple[Invite, str]:
        """Create an invite; the raw code is returned exactly once."""
        code = generate_invite_code()
        invite = Invite(
            code_hash=hash_token(code),
            created_by=created_by,
            expires_at=calculate_invite_expiry(),
            note=note,
        )
        self.db.add(invite)
        await self.db.commit()
        await self.db.refresh(invite)
        return invite, code

    async def list_invites(self) -> list[Invite]:
        result = await self.db.execute(select(Invite).order_by(Invite.created_at.desc()).limit(100))
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def _new_session(self, user_id: UUID, ip_address: str | None, user_agent: str | None) -> tuple[AuthSession, str]:
        """Create a session row; return (session, raw_token)."""
        raw_token = generate_session_token()
        session = AuthSession(
            user_id=user_id,
            token_hash=hash_token(raw_token),
            csrf_token=generate_csrf_token(),
            expires_at=calculate_session_expiry(),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return session, raw_token

    async def register_user(
        self, request: RegisterRequest, ip_address: str
    ) -> tuple[User, AuthSession, str]:
        """Register with invite; consume invite in the same transaction."""
        valid, error = validate_username(request.username)
        if not valid:
            raise ValueError(error)

        valid, error = validate_password(request.password)
        if not valid:
            raise ValueError(error)

        valid, error = validate_display_name(request.display_name)
        if not valid:
            raise ValueError(error)

        invite = await self._get_valid_invite(hash_token(request.invite_code.strip()))
        if not invite:
            raise ValueError("邀请码无效或已过期")

        username_normalized = normalize_username(request.username)
        result = await self.db.execute(
            select(User).where(User.username_normalized == username_normalized)
        )
        if result.scalar_one_or_none():
            raise ValueError("用户名已存在")

        user = User(
            username_normalized=username_normalized,
            display_name=request.display_name,
            password_hash=hash_password(request.password),
            role="member",
            status="active",
        )
        self.db.add(user)
        await self.db.flush()

        # Consume invite in the same transaction as user creation
        invite.used_by = user.id
        invite.used_at = datetime.now(tz=None)

        self.db.add(Profile(user_id=user.id, version=1))
        self.db.add(UserState(user_id=user.id, planning_revision=1))

        session, raw_token = self._new_session(user.id, ip_address, None)
        self.db.add(session)

        await self.db.commit()
        await self.db.refresh(user)
        await self.db.refresh(session)
        return user, session, raw_token

    async def login_user(
        self, request: LoginRequest, ip_address: str, user_agent: str | None = None
    ) -> tuple[User, AuthSession, str]:
        """Login; uniform error for unknown user and wrong password."""
        username_normalized = normalize_username(request.username)

        result = await self.db.execute(
            select(User)
            .where(User.username_normalized == username_normalized)
            .where(User.status == "active")
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(request.password, user.password_hash):
            await self.record_auth_attempt(request.username, ip_address, success=False)
            await self.db.commit()
            raise ValueError("用户名或密码错误")

        session, raw_token = self._new_session(user.id, ip_address, user_agent)
        self.db.add(session)
        await self.record_auth_attempt(request.username, ip_address, success=True)
        await self.db.commit()
        await self.db.refresh(session)
        return user, session, raw_token

    async def get_session_by_token(self, raw_token: str) -> AuthSession | None:
        """Load a live session from a raw cookie token."""
        result = await self.db.execute(
            select(AuthSession)
            .where(AuthSession.token_hash == hash_token(raw_token))
            .where(AuthSession.revoked_at.is_(None))
            .where(AuthSession.expires_at > datetime.now(tz=None))
        )
        return result.scalar_one_or_none()

    async def logout_user(self, session: AuthSession) -> None:
        session.revoked_at = datetime.now(tz=None)
        await self.db.commit()

    async def change_password(
        self, user: User, current_session: AuthSession, current_password: str, new_password: str
    ) -> None:
        """Change password and revoke all other sessions."""
        if not verify_password(current_password, user.password_hash):
            raise ValueError("当前密码错误")

        user.password_hash = hash_password(new_password)
        await self.db.flush()

        result = await self.db.execute(
            select(AuthSession)
            .where(AuthSession.user_id == user.id)
            .where(AuthSession.revoked_at.is_(None))
            .where(AuthSession.id != current_session.id)
        )
        for other in result.scalars().all():
            other.revoked_at = datetime.now(tz=None)

        await self.db.commit()

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    async def create_password_reset(self, username: str, created_by: UUID) -> tuple[PasswordResetToken, str]:
        """Create a one-time reset token (admin CLI)."""
        result = await self.db.execute(
            select(User).where(User.username_normalized == normalize_username(username))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("用户不存在")

        raw_token = generate_password_reset_token()
        token_row = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=calculate_password_reset_expiry(),
            created_by=created_by,
        )
        self.db.add(token_row)
        await self.db.commit()
        await self.db.refresh(token_row)
        return token_row, raw_token

    async def reset_password(self, raw_token: str, new_password: str) -> User:
        """Reset password with a one-time token; revoke all sessions."""
        result = await self.db.execute(
            select(PasswordResetToken)
            .where(PasswordResetToken.token_hash == hash_token(raw_token))
            .where(PasswordResetToken.used_at.is_(None))
            .where(PasswordResetToken.expires_at > datetime.now(tz=None))
        )
        token_row = result.scalar_one_or_none()
        if not token_row:
            raise ValueError("重置令牌无效或已过期")

        user_result = await self.db.execute(select(User).where(User.id == token_row.user_id))
        user = user_result.scalar_one_or_none()
        if not user or user.status != "active":
            raise ValueError("用户不可用")

        user.password_hash = hash_password(new_password)
        token_row.used_at = datetime.now(tz=None)

        sessions = await self.db.execute(
            select(AuthSession)
            .where(AuthSession.user_id == user.id)
            .where(AuthSession.revoked_at.is_(None))
        )
        for session in sessions.scalars().all():
            session.revoked_at = datetime.now(tz=None)

        await self.db.commit()
        return user
