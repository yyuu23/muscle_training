"""
Profile API router (plan §6.2)
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.profiles.schemas import (
    FactSupersedeRequest,
    MemoryCandidateResolveRequest,
    MemoryCandidateResponse,
    ProfileFactCreateRequest,
    ProfileFactResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    ProfileWithFactsResponse,
)
from app.modules.profiles.service import ProfileService
from app.services.planning import get_user_state

router = APIRouter()


@router.get("", response_model=ProfileWithFactsResponse)
async def get_my_profile(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Core profile, active facts and planning revision."""
    service = ProfileService(db)
    profile = await service.get_or_create_profile(user.id)
    facts = await service.get_active_facts(user.id)
    state = await get_user_state(db, user.id)
    await db.commit()

    return ProfileWithFactsResponse(
        profile=ProfileResponse.model_validate(profile),
        facts=[ProfileFactResponse.model_validate(f) for f in facts],
        planning_revision=state.planning_revision,
    )


@router.patch("", response_model=ProfileResponse)
async def update_my_profile(
    request_data: ProfileUpdateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Update profile fields with expected_version."""
    service = ProfileService(db)
    profile = await service.update_profile(user.id, request_data)
    return ProfileResponse.model_validate(profile)


@router.get("/completeness")
async def profile_completeness(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Missing intake fields for onboarding hints (plan §8.1)."""
    service = ProfileService(db)
    return await service.profile_completeness(user.id)


@router.get("/facts", response_model=list[ProfileFactResponse])
async def get_my_facts(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    service = ProfileService(db)
    facts = await service.get_active_facts(user.id)
    return [ProfileFactResponse.model_validate(f) for f in facts]


@router.post("/facts", response_model=ProfileFactResponse, status_code=201)
async def create_fact(
    request_data: ProfileFactCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Explicit form input → confirmed user fact."""
    service = ProfileService(db)
    fact = await service.create_fact(user.id, request_data)
    return ProfileFactResponse.model_validate(fact)


@router.post("/facts/{fact_id}/supersede", response_model=ProfileFactResponse)
async def supersede_fact(
    fact_id: UUID,
    request_data: FactSupersedeRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Explicitly replace a fact, keeping provenance."""
    service = ProfileService(db)
    fact = await service.supersede_fact(
        fact_id, user.id, value=request_data.value, source_ref=request_data.source_ref
    )
    return ProfileFactResponse.model_validate(fact)


@router.get("/memory-candidates", response_model=list[MemoryCandidateResponse])
async def list_memory_candidates(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
    status: str = "pending",
):
    """Pending long-term memory awaiting confirmation."""
    service = ProfileService(db)
    candidates = await service.list_candidates(user.id, status=status)
    return [MemoryCandidateResponse.model_validate(c) for c in candidates]


@router.post("/memory-candidates/{candidate_id}/resolve", response_model=MemoryCandidateResponse)
async def resolve_memory_candidate(
    candidate_id: UUID,
    request_data: MemoryCandidateResolveRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Accept (→ profile_facts) or reject a memory candidate."""
    service = ProfileService(db)
    candidate = await service.resolve_candidate(
        candidate_id, user.id, decision=request_data.decision
    )
    return MemoryCandidateResponse.model_validate(candidate)
