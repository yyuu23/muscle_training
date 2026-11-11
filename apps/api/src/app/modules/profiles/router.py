"""
Profile management API router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.profiles.schemas import (
    ProfileFactCreateRequest,
    ProfileFactResponse,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.modules.profiles.service import ProfileService

router = APIRouter()


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Get current user's profile"""
    service = ProfileService(db)
    profile = await service.get_profile(user.id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    return ProfileResponse.model_validate(profile)


@router.patch("/me", response_model=ProfileResponse)
async def update_my_profile(
    request_data: ProfileUpdateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Update current user's profile"""
    service = ProfileService(db)

    try:
        profile = await service.update_profile(user.id, request_data)
        return ProfileResponse.model_validate(profile)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/me/facts", response_model=list[ProfileFactResponse])
async def get_my_profile_facts(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Get current user's profile facts"""
    service = ProfileService(db)
    facts = await service.get_profile_facts(user.id)

    return [ProfileFactResponse.model_validate(fact) for fact in facts]


@router.post("/me/facts", response_model=ProfileFactResponse, status_code=status.HTTP_201_CREATED)
async def create_profile_fact(
    request_data: ProfileFactCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new profile fact"""
    service = ProfileService(db)

    # Get user's profile
    profile = await service.get_profile(user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    fact = await service.create_profile_fact(user.id, profile.id, request_data)
    return ProfileFactResponse.model_validate(fact)
