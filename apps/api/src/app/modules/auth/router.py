"""
Authentication API router
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import CurrentAdminUser, CurrentUser
from app.modules.auth.schemas import (
    CreateInviteRequest,
    InviteResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter()


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request_data: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Register a new user with an invite code"""
    service = AuthService(db)

    # Get client IP
    ip_address = request.client.host if request.client else "unknown"

    try:
        user, session = await service.register_user(request_data, ip_address)

        return LoginResponse(
            token=session.token,
            user=UserResponse.model_validate(user),
            expires_at=session.expires_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    request_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Login with username and password"""
    service = AuthService(db)

    # Get client IP and user agent
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")

    # Check rate limit
    if not await service.check_rate_limit(request_data.username, ip_address):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later.",
        )

    try:
        user, session = await service.login_user(request_data, ip_address, user_agent)

        return LoginResponse(
            token=session.token,
            user=UserResponse.model_validate(user),
            expires_at=session.expires_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Logout current user"""
    service = AuthService(db)

    # Get current session from user context (would need to pass session through dependency)
    # For now, we'll handle this in the dependency itself
    # await service.logout_user(current_session)

    return None


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: CurrentUser):
    """Get current user information"""
    return UserResponse.model_validate(user)


@router.post("/invites", response_model=InviteResponse)
async def create_invite(
    request_data: CreateInviteRequest,
    user: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Create an invite code (admin only)"""
    service = AuthService(db)

    invite = await service.create_invite(user.id, request_data.note)

    return InviteResponse.model_validate(invite)
