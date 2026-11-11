"""
Profile management service
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.profile import Profile, ProfileFact, UserState
from app.modules.profiles.schemas import ProfileFactCreateRequest, ProfileUpdateRequest


class ProfileService:
    """Profile management business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_profile(self, user_id: UUID) -> Profile | None:
        """Get user profile"""
        result = await self.db.execute(
            select(Profile).where(Profile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_profile(self, user_id: UUID, request: ProfileUpdateRequest) -> Profile:
        """Update user profile"""
        profile = await self.get_profile(user_id)

        if not profile:
            raise ValueError("Profile not found")

        # Update fields
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)

        # Increment version
        profile.version += 1

        # Update planning revision to trigger plan regeneration
        await self.db.execute(
            select(UserState)
            .where(UserState.user_id == user_id)
            .with_for_update()
        )

        result = await self.db.execute(
            select(UserState).where(UserState.user_id == user_id)
        )
        user_state = result.scalar_one_or_none()

        if user_state:
            user_state.planning_revision += 1

        await self.db.commit()
        await self.db.refresh(profile)

        return profile

    async def get_profile_facts(self, user_id: UUID, status: str = "active") -> list[ProfileFact]:
        """Get profile facts for user"""
        result = await self.db.execute(
            select(ProfileFact)
            .where(ProfileFact.user_id == user_id)
            .where(ProfileFact.status == status)
            .order_by(ProfileFact.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_profile_fact(
        self, user_id: UUID, profile_id: UUID, request: ProfileFactCreateRequest
    ) -> ProfileFact:
        """Create a new profile fact"""
        fact = ProfileFact(
            user_id=user_id,
            profile_id=profile_id,
            kind=request.kind,
            source=request.source,
            content=request.content,
            confidence=request.confidence,
            status="active",
            metadata=request.metadata,
        )

        self.db.add(fact)
        await self.db.commit()
        await self.db.refresh(fact)

        return fact

    async def supersede_fact(self, fact_id: UUID, superseding_fact_id: UUID) -> None:
        """Mark a fact as superseded"""
        result = await self.db.execute(
            select(ProfileFact).where(ProfileFact.id == fact_id)
        )
        fact = result.scalar_one_or_none()

        if fact:
            fact.status = "superseded"
            fact.superseded_by = superseding_fact_id
            await self.db.commit()
