"""
Authentication utilities (plan §9.2)

- 256-bit random tokens; database stores only SHA-256 hashes.
- Session absolute validity 7 days; invites 72 hours, one-time use.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

from app.config import get_settings

settings = get_settings()


def normalize_username(username: str) -> str:
    """Normalize username for storage and comparison."""
    return username.lower().strip()


def hash_token(token: str) -> str:
    """Hash a raw token for storage (SHA-256 hex)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_session_token() -> str:
    """Generate a 256-bit secure random session token (url-safe)."""
    return secrets.token_urlsafe(32)


def generate_csrf_token() -> str:
    """Generate a random CSRF token bound to the session."""
    return secrets.token_urlsafe(32)


def generate_invite_code() -> str:
    """Generate a one-time invite code."""
    return secrets.token_urlsafe(18)


def generate_password_reset_token() -> str:
    """Generate a one-time password reset token."""
    return secrets.token_urlsafe(32)


def calculate_session_expiry(now: datetime | None = None) -> datetime:
    """Session absolute expiry (default 7 days)."""
    base = now or datetime.now(tz=None)
    return base + timedelta(days=settings.session_expire_days)


def calculate_invite_expiry(now: datetime | None = None) -> datetime:
    """Invite validity: 72 hours."""
    base = now or datetime.now(tz=None)
    return base + timedelta(hours=settings.invite_code_expire_hours)


def calculate_password_reset_expiry(now: datetime | None = None) -> datetime:
    """Password reset token validity: 24 hours."""
    base = now or datetime.now(tz=None)
    return base + timedelta(hours=24)
