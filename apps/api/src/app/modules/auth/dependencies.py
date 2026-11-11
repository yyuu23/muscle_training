"""
Authentication dependencies for FastAPI
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import AuthSession, User
from app.db.session import get_db_session


async def get_current_session(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db_session),
) -> AuthSession:
    """
    Get current authenticated session from Authorization header

    Args:
        authorization: Authorization header value
        db: Database session

    Returns:
        AuthSession object

    Raises:
        HTTPException: If token is invalid or expired
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    # Query session
    result = await db.execute(
        select(AuthSession)
        .where(AuthSession.token == token)
        .where(AuthSession.revoked == False)  # noqa: E712
        .where(AuthSession.expires_at > datetime.now())
    )

    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last used timestamp
    session.last_used_at = datetime.now()
    await db.commit()

    return session


async def get_current_user(
    session: AuthSession = Depends(get_current_session),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Get current authenticated user

    Args:
        session: Current session
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If user not found or deleted
    """
    result = await db.execute(
        select(User)
        .where(User.id == session.user_id)
        .where(User.status == "active")
    )

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


async def get_current_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    """
    Get current authenticated admin user

    Args:
        user: Current user

    Returns:
        User object

    Raises:
        HTTPException: If user is not admin
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return user


# Type aliases for dependency injection
CurrentSession = Annotated[AuthSession, Depends(get_current_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdminUser = Annotated[User, Depends(get_current_admin_user)]
