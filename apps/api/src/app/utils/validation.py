"""
Validation utilities
"""

import re


def validate_username(username: str) -> tuple[bool, str | None]:
    """
    Validate username format

    Args:
        username: Username to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"

    if len(username) < 3:
        return False, "Username must be at least 3 characters"

    if len(username) > 50:
        return False, "Username must be at most 50 characters"

    # Allow alphanumeric, underscore, hyphen, Chinese characters
    if not re.match(r'^[\w一-鿿-]+$', username):
        return False, "Username can only contain letters, numbers, underscores, hyphens, and Chinese characters"

    return True, None


def validate_password(password: str) -> tuple[bool, str | None]:
    """
    Validate password strength

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"

    if len(password) < 12:
        return False, "Password must be at least 12 characters"

    if len(password) > 128:
        return False, "Password must be at most 128 characters"

    return True, None


def validate_display_name(display_name: str) -> tuple[bool, str | None]:
    """
    Validate display name

    Args:
        display_name: Display name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not display_name:
        return False, "Display name is required"

    if len(display_name) < 1:
        return False, "Display name cannot be empty"

    if len(display_name) > 100:
        return False, "Display name must be at most 100 characters"

    return True, None
