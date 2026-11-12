"""
Planning revision management (plan §5.9)

planning_revision increments when:
- training-related profile fields change
- confirmed constraints or preferences change
- body observations update
- training records are added, corrected or deleted
- the active plan changes

Plain chat and backup downloads never increment it.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.catalog import PlanVersion
from app.db.models.profile import UserState


async def get_user_state(db: AsyncSession, user_id) -> UserState:
    """Load or create user state."""
    result = await db.execute(select(UserState).where(UserState.user_id == user_id))
    state = result.scalar_one_or_none()
    if state is None:
        state = UserState(user_id=user_id, planning_revision=1)
        db.add(state)
        await db.flush()
    return state


async def bump_planning_revision(db: AsyncSession, user_id) -> int:
    """Increment planning_revision. Caller commits the transaction."""
    state = await get_user_state(db, user_id)
    state.planning_revision += 1
    await db.flush()
    return state.planning_revision


async def get_active_plan(db: AsyncSession, user_id) -> PlanVersion | None:
    """Load the user's active plan."""
    result = await db.execute(
        select(PlanVersion)
        .where(PlanVersion.user_id == user_id)
        .where(PlanVersion.status == "active")
    )
    return result.scalar_one_or_none()


def contexts_match(
    state: UserState,
    plan: PlanVersion,
    current_profile_version: int | None,
) -> bool:
    """Whether a candidate plan's recorded basis is still current.

    Strict triple check (plan §5.9): a late-generated plan built on a
    stale basis must never overwrite newer facts.
    """
    if plan.basis_planning_revision is not None:
        if plan.basis_planning_revision != state.planning_revision:
            return False
    if plan.basis_active_plan_id is not None:
        if plan.basis_active_plan_id != state.active_plan_id:
            return False
    if plan.basis_profile_version is not None and current_profile_version is not None:
        if plan.basis_profile_version != current_profile_version:
            return False
    return True
