"""
Authentication API router (plan §6.2)
"""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ErrorCode, error_response
from app.db.session import get_db_session
from app.modules.auth.dependencies import (
    CurrentAdminUser,
    CurrentSession,
    CurrentUser,
    build_session_cookie,
    clear_session_cookie,
)
from app.modules.auth.schemas import (
    AuthMeResponse,
    ChangePasswordRequest,
    InviteCreatedResponse,
    InviteCreateRequest,
    InviteResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionTokenResponse,
    UserResponse,
)
from app.modules.auth.service import AuthService
from app.services.capabilities import build_capabilities

router = APIRouter()


@router.post("/register", response_model=SessionTokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request_data: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
):
    """Register a new user with an invite code; sets the session cookie."""
    service = AuthService(db)
    ip_address = request.client.host if request.client else "unknown"

    try:
        user, session, raw_token = await service.register_user(request_data, ip_address)
    except ValueError as e:
        return error_response(ErrorCode.VALIDATION_ERROR, str(e), status_code=400)

    cookie = build_session_cookie(raw_token)
    response.set_cookie(**cookie)

    return SessionTokenResponse(
        user=UserResponse.model_validate(user),
        csrf_token=session.csrf_token,
    )


@router.post("/login", response_model=SessionTokenResponse)
async def login(
    request_data: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
):
    """Login; sets the session cookie."""
    service = AuthService(db)
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")

    if not await service.check_rate_limit(request_data.username, ip_address):
        return error_response(
            ErrorCode.RATE_LIMITED,
            "尝试次数过多，请稍后再试",
            status_code=429,
        )

    try:
        user, session, raw_token = await service.login_user(request_data, ip_address, user_agent)
    except ValueError as e:
        return error_response(ErrorCode.AUTH_REQUIRED, str(e), status_code=401)

    response.set_cookie(**build_session_cookie(raw_token))

    return SessionTokenResponse(
        user=UserResponse.model_validate(user),
        csrf_token=session.csrf_token,
    )


@router.get("/me", response_model=AuthMeResponse)
async def me(
    user: CurrentUser,
    session: CurrentSession,
    db: AsyncSession = Depends(get_db_session),
):
    """Current user, CSRF token and capability states."""
    return AuthMeResponse(
        user=UserResponse.model_validate(user),
        csrf_token=session.csrf_token,
        capabilities=await build_capabilities(db),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    session: CurrentSession,
    db: AsyncSession = Depends(get_db_session),
):
    """Revoke the current session and clear the cookie."""
    service = AuthService(db)
    await service.logout_user(session)
    response.delete_cookie(**clear_session_cookie())
    return None


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request_data: ChangePasswordRequest,
    user: CurrentUser,
    session: CurrentSession,
    db: AsyncSession = Depends(get_db_session),
):
    """Change password; revokes all other sessions."""
    service = AuthService(db)
    try:
        await service.change_password(
            user, session, request_data.current_password, request_data.new_password
        )
    except ValueError as e:
        return error_response(ErrorCode.VALIDATION_ERROR, str(e), status_code=400)
    return None


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    request_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Reset password with a one-time token; revokes all sessions."""
    service = AuthService(db)
    try:
        await service.reset_password(request_data.token, request_data.new_password)
    except ValueError as e:
        return error_response(ErrorCode.VALIDATION_ERROR, str(e), status_code=400)
    return None


@router.post("/invites", response_model=InviteCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    request_data: InviteCreateRequest,
    admin: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a one-time invite code (admin)."""
    service = AuthService(db)
    invite, code = await service.create_invite(admin.id, request_data.note)
    return InviteCreatedResponse(
        invite=InviteResponse.model_validate(invite),
        code=code,
    )


@router.get("/invites", response_model=list[InviteResponse])
async def list_invites(
    admin: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
):
    """List invites (admin)."""
    service = AuthService(db)
    invites = await service.list_invites()
    return [InviteResponse.model_validate(invite) for invite in invites]
