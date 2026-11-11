"""
Authentication utilities
"""

import secrets
from datetime import datetime, timedelta

from app.config import get_settings

settings = get_settings()


def normalize_username(username: str) -> str:
    """
    Normalize username for storage and comparison

    Args:
        username: Raw username input

    Returns:
        Normalized username (lowercase, stripped)
    """
    return username.lower().strip()


def generate_session_token() -> str:
    """
    Generate a secure random session token

    Returns:
        URL-safe random token (48 bytes = 64 characters base64)
    """
    return secrets.token_urlsafe(48)


def generate_invite_code() -> str:
    """
    Generate a random invite code

    Returns:
        URL-safe random code (24 bytes = 32 characters base64)
    """
    return secrets.token_urlsafe(24)


def calculate_session_expiry() -> datetime:
    """
    Calculate session expiry time

    Returns:
        Datetime when session should expire
    """
    return datetime.now(tz=None) + timedelta(days=settings.session_expire_days)


def calculate_invite_expiry() -> datetime:
    """
    Calculate invite code expiry time

    Returns:
        Datetime when invite should expire
    """
    return datetime.now(tz=None) + timedelta(hours=settings.invite_code_expire_hours)
