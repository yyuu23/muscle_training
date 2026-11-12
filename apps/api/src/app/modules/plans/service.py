"""
Plan service (plan §5.4 / §5.9)

- Drafts are immutable; changes create new drafts.
- Activation locks user_state and validates the full basis triple;
  stale basis → 409 PLAN_CONTEXT_STALE.
"""

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, ErrorCode
from app.db.models.catalog import PlanVersion, TrainingTemplate
from app.db.models.profile import Profile, UserState
from app.modules.plans.diff import diff_plans
from app.modules.plans.schemas import PlanContent, PlanValidationIssue
from app.modules.plans.validators import validate_plan_content
from app.services.planning import contexts_match, get_user_state


class PlanService:
    """Plan version business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_active_plan(self, user_id: UUID) -> PlanVersion | None:
        result = await self.db.execute(
            select(PlanVersion)
            .where(PlanVersion.user_id == user_id)
            .where(PlanVersion.status == "active")
        )
        return result.scalar_one_or_none()

    async def get_plan(self, plan_id: UUID, user_id: UUID) -> PlanVersion | None:
        plan = await self.db.get(PlanVersion, plan_id)
        if plan is None or plan.user_id != user_id:
            return None
        return plan

    async def list_plans(
        self, user_id: UUID, *, limit: int = 30, cursor: str | None = None
    ) -> tuple[list[PlanVersion], str | None]:
        query = (
            select(PlanVersion)
            .where(PlanVersion.user_id == user_id)
            .order_by(PlanVersion.sequence_number.desc())
            .limit(limit + 1)
        )
        if cursor:
            query = query.where(PlanVersion.sequence_number < int(cursor))

        result = await self.db.execute(query)
        rows = list(result.scalars().all())

        next_cursor = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = str(rows[-1].sequence_number)
        return rows, next_cursor

    async def plan_detail(self, plan: PlanVersion, user_id: UUID) -> dict:
        """Plan + validation issues + diff vs current active."""
        try:
            content = PlanContent.model_validate(plan.content)
        except Exception as exc:
            content = None
            issues = [
                PlanValidationIssue(code="content_invalid", message=f"计划正文无法解析: {exc}"[:300])
            ]
        else:
            template = None
            if plan.template_versions:
                first = plan.template_versions[0]
                template_id = first.get("template_id") if isinstance(first, dict) else None
                if template_id:
                    template = await self.db.get(TrainingTemplate, UUID(str(template_id)))
            issues = await validate_plan_content(self.db, user_id, content, template)

        active = await self.get_active_plan(user_id)
        diff = None
        if content is not None and (active is None or active.id != plan.id):
            try:
                old_content = PlanContent.model_validate(active.content) if active else None
                diff = diff_plans(old_content, content)
            except Exception:
                diff = None

        return {
            "plan": plan,
            "validation_issues": issues,
            "diff_vs_active": diff,
        }

    # ------------------------------------------------------------------
    # Draft creation (agent / manual)
    # ------------------------------------------------------------------

    async def create_draft(
        self,
        user_id: UUID,
        *,
        content: PlanContent,
        template_versions: list | None,
        model_run_id: UUID | None,
        rationale: str | None,
    ) -> PlanVersion:
        """Validate then save an immutable draft with recorded basis."""
        template = None
        if template_versions:
            first = template_versions[0]
            template_id = first.get("template_id") if isinstance(first, dict) else None
            if template_id:
                template = await self.db.get(TrainingTemplate, UUID(str(template_id)))

        issues = await validate_plan_content(self.db, user_id, content, template)
        blocking = [i for i in issues if i.code != "exercise_version_mismatch"]
        if blocking:
            raise ApiError(
                ErrorCode.MODEL_OUTPUT_INVALID,
                "计划候选未通过领域校验",
                {"issues": [i.model_dump() for i in blocking]},
            )

        state = await get_user_state(self.db, user_id)
        profile = (
            await self.db.execute(select(Profile).where(Profile.user_id == user_id))
        ).scalar_one_or_none()

        next_seq = (await self._next_sequence(user_id)) + 1

        draft = PlanVersion(
            user_id=user_id,
            sequence_number=next_seq,
            status="draft",
            content=json.loads(content.model_dump_json()),
            basis_profile_version=profile.version if profile else None,
            basis_planning_revision=state.planning_revision,
            basis_active_plan_id=state.active_plan_id,
            template_versions=template_versions,
            model_run_id=model_run_id,
            rationale=rationale,
        )
        self.db.add(draft)
        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    async def _next_sequence(self, user_id: UUID) -> int:
        result = await self.db.execute(
            select(func.max(PlanVersion.sequence_number)).where(PlanVersion.user_id == user_id)
        )
        return result.scalar() or 0

    # ------------------------------------------------------------------
    # Activation (plan §5.9)
    # ------------------------------------------------------------------

    async def activate_plan(
        self,
        plan_id: UUID,
        user_id: UUID,
        *,
        expected_basis_planning_revision: int,
    ) -> tuple[PlanVersion, PlanVersion | None]:
        """Adopt a draft. Locks user_state; validates the full basis triple."""
        # Lock user_state row
        locked = await self.db.execute(
            select(UserState).where(UserState.user_id == user_id).with_for_update()
        )
        state = locked.scalar_one_or_none()
        if state is None:
            state = UserState(user_id=user_id, planning_revision=1)
            self.db.add(state)
            await self.db.flush()

        candidate = await self.get_plan(plan_id, user_id)
        if candidate is None:
            raise ApiError(ErrorCode.NOT_FOUND, "计划不存在")
        if candidate.status != "draft":
            raise ApiError(ErrorCode.VALIDATION_ERROR, "只有草稿状态的计划可以采用")

        # Client-side guard: the revision the user saw must match what we hold
        if expected_basis_planning_revision != state.planning_revision:
            raise ApiError(ErrorCode.PLAN_CONTEXT_STALE, "候选计划所依据的数据已变化，请重新生成")

        profile = (
            await self.db.execute(select(Profile).where(Profile.user_id == user_id))
        ).scalar_one_or_none()

        if not contexts_match(
            state, candidate, profile.version if profile else None
        ):
            raise ApiError(ErrorCode.PLAN_CONTEXT_STALE, "候选计划所依据的数据已变化，请重新生成")

        # Domain validation must pass before activation
        template = None
        if candidate.template_versions:
            first = candidate.template_versions[0]
            template_id = first.get("template_id") if isinstance(first, dict) else None
            if template_id:
                template = await self.db.get(TrainingTemplate, UUID(str(template_id)))
        content = PlanContent.model_validate(candidate.content)
        issues = await validate_plan_content(self.db, user_id, content, template)
        if issues:
            raise ApiError(
                ErrorCode.MODEL_OUTPUT_INVALID,
                "计划未通过约束校验，不能采用",
                {"issues": [i.model_dump() for i in issues]},
            )

        # Supersede current active in the same transaction
        superseded: PlanVersion | None = None
        if state.active_plan_id is not None:
            superseded = await self.get_plan(state.active_plan_id, user_id)
            if superseded is not None and superseded.status == "active":
                superseded.status = "superseded"
                superseded.superseded_at = datetime.now(tz=None)

        candidate.status = "active"
        candidate.activated_at = datetime.now(tz=None)

        state.active_plan_id = candidate.id
        state.planning_revision += 1  # active plan change increments revision (plan §5.9)

        await self.db.commit()
        await self.db.refresh(candidate)
        return candidate, superseded
