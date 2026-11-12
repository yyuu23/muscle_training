"""
Profile service (plan §5.3 / §7.11)

- profile_facts is the single source of confirmed preferences/limits.
- model_inference never becomes a confirmed fact directly.
- Training-relevant changes bump planning_revision.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, ErrorCode
from app.db.models.profile import MemoryCandidate, Profile, ProfileFact
from app.modules.profiles.schemas import ProfileFactCreateRequest, ProfileUpdateRequest
from app.services.planning import bump_planning_revision


class ProfileService:
    """Profile and memory business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    async def get_profile(self, user_id: UUID) -> Profile | None:
        result = await self.db.execute(select(Profile).where(Profile.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_or_create_profile(self, user_id: UUID) -> Profile:
        profile = await self.get_profile(user_id)
        if profile is None:
            profile = Profile(user_id=user_id, version=1)
            self.db.add(profile)
            await self.db.flush()
        return profile

    async def update_profile(self, user_id: UUID, request: ProfileUpdateRequest) -> Profile:
        """Update profile with optimistic locking; bumps planning revision."""
        profile = await self.get_profile(user_id)
        if profile is None:
            raise ApiError(ErrorCode.NOT_FOUND, "档案不存在")

        if profile.version != request.expected_version:
            raise ApiError(ErrorCode.VERSION_CONFLICT, "档案已被修改，请刷新后重试")

        changes = request.model_dump(exclude_unset=True, exclude={"expected_version"})
        if not changes:
            return profile

        training_related = {
            "goal",
            "sessions_per_week",
            "minutes_per_session",
            "available_weekdays",
            "equipment",
            "available_load_increments",
            "training_experience_months",
        }

        for field, value in changes.items():
            setattr(profile, field, value)
        profile.version += 1

        await self.db.flush()
        if changes.keys() & training_related:
            await bump_planning_revision(self.db, user_id)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def profile_completeness(self, user_id: UUID) -> dict:
        """Which required intake fields are still missing (plan §8.1 onboarding)."""
        profile = await self.get_profile(user_id)
        required = {
            "goal": profile.goal if profile else None,
            "training_experience_months": profile.training_experience_months if profile else None,
            "sessions_per_week": profile.sessions_per_week if profile else None,
            "minutes_per_session": profile.minutes_per_session if profile else None,
            "equipment": profile.equipment if profile else None,
        }
        missing = [field for field, value in required.items() if value in (None, [], "")]
        return {"missing_fields": missing, "complete": not missing}

    # ------------------------------------------------------------------
    # Facts
    # ------------------------------------------------------------------

    async def get_active_facts(self, user_id: UUID) -> list[ProfileFact]:
        result = await self.db.execute(
            select(ProfileFact)
            .where(ProfileFact.user_id == user_id)
            .where(ProfileFact.superseded_by.is_(None))
            .order_by(ProfileFact.created_at)
        )
        return list(result.scalars().all())

    async def create_fact(
        self,
        user_id: UUID,
        request: ProfileFactCreateRequest,
        *,
        provenance: str = "user_statement",
    ) -> ProfileFact:
        """Explicit form input → confirmed fact directly (plan §7.11)."""
        profile = await self.get_or_create_profile(user_id)

        # Same (kind, fact_key): supersede previous instead of duplicating
        result = await self.db.execute(
            select(ProfileFact)
            .where(ProfileFact.user_id == user_id)
            .where(ProfileFact.kind == request.kind)
            .where(ProfileFact.fact_key == request.fact_key)
            .where(ProfileFact.superseded_by.is_(None))
        )
        previous = result.scalar_one_or_none()

        now = datetime.now(tz=None)
        fact = ProfileFact(
            user_id=user_id,
            profile_id=profile.id,
            kind=request.kind,
            fact_key=request.fact_key,
            value=request.value,
            provenance=provenance,
            source_ref=request.source_ref,
            confirmed_at=now,
            effective_at=now,
        )
        self.db.add(fact)
        await self.db.flush()

        if previous is not None:
            previous.superseded_by = fact.id
            previous.superseded_at = now

        await self.db.flush()
        await bump_planning_revision(self.db, user_id)
        await self.db.commit()
        await self.db.refresh(fact)
        return fact

    async def supersede_fact(
        self, fact_id: UUID, user_id: UUID, *, value: str, source_ref: str | None
    ) -> ProfileFact:
        """Explicitly replace a fact with a new one, keeping provenance."""
        result = await self.db.execute(
            select(ProfileFact)
            .where(ProfileFact.id == fact_id)
            .where(ProfileFact.user_id == user_id)
        )
        old = result.scalar_one_or_none()
        if old is None:
            raise ApiError(ErrorCode.NOT_FOUND, "事实不存在")
        if old.superseded_by is not None:
            raise ApiError(ErrorCode.VALIDATION_ERROR, "该事实已被替代")

        now = datetime.now(tz=None)
        new_fact = ProfileFact(
            user_id=user_id,
            profile_id=old.profile_id,
            kind=old.kind,
            fact_key=old.fact_key,
            value=value,
            provenance=old.provenance,
            source_ref=source_ref or old.source_ref,
            confirmed_at=now,
            effective_at=now,
        )
        self.db.add(new_fact)
        await self.db.flush()

        old.superseded_by = new_fact.id
        old.superseded_at = now

        await self.db.flush()
        await bump_planning_revision(self.db, user_id)
        await self.db.commit()
        await self.db.refresh(new_fact)
        return new_fact

    # ------------------------------------------------------------------
    # Memory candidates (plan §7.11)
    # ------------------------------------------------------------------

    async def list_candidates(self, user_id: UUID, *, status: str = "pending") -> list[MemoryCandidate]:
        result = await self.db.execute(
            select(MemoryCandidate)
            .where(MemoryCandidate.user_id == user_id)
            .where(MemoryCandidate.status == status)
            .order_by(MemoryCandidate.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_candidate(
        self,
        user_id: UUID,
        *,
        proposed_fact: str,
        source_kind: str,
        source_ref: str | None,
        metadata: dict | None = None,
    ) -> MemoryCandidate:
        """Create a candidate awaiting user confirmation (agent extraction)."""
        candidate = MemoryCandidate(
            user_id=user_id,
            proposed_fact=proposed_fact,
            source_kind=source_kind,
            source_ref=source_ref,
            status="pending",
            meta=metadata,
        )
        self.db.add(candidate)
        await self.db.commit()
        await self.db.refresh(candidate)
        return candidate

    async def resolve_candidate(
        self, candidate_id: UUID, user_id: UUID, *, decision: str
    ) -> MemoryCandidate:
        """Accept writes profile_facts; reject just marks resolved."""
        result = await self.db.execute(
            select(MemoryCandidate)
            .where(MemoryCandidate.id == candidate_id)
            .where(MemoryCandidate.user_id == user_id)
        )
        candidate = result.scalar_one_or_none()
        if candidate is None:
            raise ApiError(ErrorCode.NOT_FOUND, "候选不存在")
        if candidate.status != "pending":
            raise ApiError(ErrorCode.VALIDATION_ERROR, "候选已被处理")

        now = datetime.now(tz=None)
        candidate.resolved_at = now

        if decision == "accept":
            meta = candidate.meta or {}
            profile = await self.get_or_create_profile(user_id)

            fact = ProfileFact(
                user_id=user_id,
                profile_id=profile.id,
                kind=meta.get("kind", "training_limitation"),
                fact_key=meta.get("fact_key", candidate.proposed_fact[:200]),
                value=candidate.proposed_fact,
                provenance=candidate.source_kind,
                source_ref=candidate.source_ref,
                confirmed_at=now,
                effective_at=now,
            )
            self.db.add(fact)
            await self.db.flush()
            candidate.status = "accepted"
            await bump_planning_revision(self.db, user_id)
        else:
            candidate.status = "rejected"

        await self.db.commit()
        await self.db.refresh(candidate)
        return candidate
