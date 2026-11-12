"""
Auth dependencies (plan §9.2)

- Session from HttpOnly cookie; CSRF token verified on writes.
- Cross-user access to private entities must surface as 404 at the
  module level; these dependencies only establish identity.
"""

import hmac
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ErrorCode
from app.config import get_settings
from app.db.models.auth import AuthSession, User
from app.db.session import get_db_session

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def session_cookie_name() -> str:
    """Production uses the __Host- prefix without a Domain attribute."""
    settings = get_settings()
    if settings.python_env == "production":
        return "__Host-session"
    return "session"


def build_session_cookie(token: str) -> dict:
    """Cookie parameters for a newly issued session."""
    settings = get_settings()
    return {
        "key": session_cookie_name(),
        "value": token,
        "max_age": settings.session_expire_days * 24 * 3600,
        "httponly": True,
        "secure": settings.python_env == "production",
        "samesite": "lax",
        "path": "/",
    }


def clear_session_cookie() -> dict:
    """Arguments for Response.delete_cookie() (no value/max_age — those
    belong to set_cookie; delete_cookie clears by key+path)."""
    return {
        "key": session_cookie_name(),
        "path": "/",
        "httponly": True,
        "secure": get_settings().python_env == "production",
        "samesite": "lax",
    }


async def get_current_session(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> AuthSession:
    """Load session from cookie; verify CSRF for non-safe methods."""
    raw_token = request.cookies.get(session_cookie_name())
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": ErrorCode.AUTH_REQUIRED, "message": "未登录"},
        )

    from app.modules.auth.service import AuthService

    service = AuthService(db)
    session = await service.get_session_by_token(raw_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": ErrorCode.AUTH_REQUIRED, "message": "会话无效或已过期"},
        )

    # CSRF verification for state-changing requests (plan §9.2)
    if request.method not in SAFE_METHODS:
        if not x_csrf_token or not hmac.compare_digest(x_csrf_token, session.csrf_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": ErrorCode.ACCESS_DENIED, "message": "缺少或错误的 CSRF 令牌"},
            )

    session.last_used_at = datetime.now(tz=None)
    return session


async def get_current_user(
    session: AuthSession = Depends(get_current_session),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    result = await db.execute(
        select(User)
        .where(User.id == session.user_id)
        .where(User.status == "active")
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": ErrorCode.AUTH_REQUIRED, "message": "用户不存在或已停用"},
        )
    return user


async def get_current_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": ErrorCode.ACCESS_DENIED, "message": "需要管理员权限"},
        )
    return user


# Type aliases for dependency injection
CurrentSession = Annotated[AuthSession, Depends(get_current_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdminUser = Annotated[User, Depends(get_current_admin_user)]
