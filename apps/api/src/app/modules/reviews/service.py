"""
Reviews service (plan §7.12)

- POST /reviews/weekly: same-basis result reuse or new job.
- Model interprets statistics only; data-insufficient weeks skip the
  model entirely.
- Corrections/late logs mark earlier reviews stale.
"""

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.limits import record_model_run, reserve_budget
from app.agent.orchestrator import load_prompt, prompt_version
from app.agent.output_validation import build_repair_prompt, parse_structured
from app.agent.schemas import WeeklyReviewNarrative
from app.api.errors import ApiError, ErrorCode
from app.config import get_settings
from app.db.models.operations import WeeklyReview
from app.modules.reviews.builder import (
    build_insufficient_data_review,
    build_weekly_statistics,
    week_start_for,
)
from app.providers import get_chat_provider
from app.providers.interfaces import ChatMessage, ChatRequest

MAX_REPAIRS = 1


class ReviewService:
    """Weekly review business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def get_or_create_review(self, user_id: UUID, *, week_start: datetime | None = None) -> WeeklyReview:
        """Same planning_revision → reuse; else create a fresh review."""
        from app.services.planning import get_user_state

        state = await get_user_state(self.db, user_id)
        start = week_start or week_start_for(datetime.now(tz=None))

        existing = (
            await self.db.execute(
                select(WeeklyReview)
                .where(WeeklyReview.user_id == user_id)
                .where(WeeklyReview.week_start == start)
                .where(WeeklyReview.data_revision == state.planning_revision)
                .where(WeeklyReview.stale.is_(False))
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        review = await self._generate(user_id, start, state.planning_revision)
        return review

    async def _generate(self, user_id: UUID, week_start: datetime, planning_revision: int) -> WeeklyReview:
        """Deterministic statistics + (optional) model narrative."""
        statistics = await build_weekly_statistics(self.db, user_id, week_start)

        if not statistics["data_sufficient"]:
            fixed = build_insufficient_data_review(statistics)
            review = WeeklyReview(
                user_id=user_id,
                week_start=week_start,
                data_revision=planning_revision,
                data_cutoff_at=datetime.fromisoformat(statistics["data_cutoff_at"]),
                statistics=statistics,
                narrative=fixed["narrative_markdown"],
                stale=False,
            )
            self.db.add(review)
            await self.db.commit()
            await self.db.refresh(review)
            return review

        narrative_payload = await self._model_narrative(user_id, statistics)
        review = WeeklyReview(
            user_id=user_id,
            week_start=week_start,
            data_revision=planning_revision,
            data_cutoff_at=datetime.fromisoformat(statistics["data_cutoff_at"]),
            statistics=statistics,
            narrative=narrative_payload["narrative_markdown"],
            stale=False,
        )
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def _model_narrative(self, user_id: UUID, statistics: dict) -> dict:
        """One model call (+≤1 repair) to interpret given statistics."""
        chat = get_chat_provider()
        await reserve_budget(self.db, 10)

        prompt_name = "weekly_review"
        payload = json.dumps(statistics, ensure_ascii=False)
        messages = [
            ChatMessage(role="system", content=load_prompt("system")),
            ChatMessage(role="system", content=load_prompt(prompt_name)),
            ChatMessage(role="user", content=payload),
        ]
        result = await chat.generate(ChatRequest(messages=messages, operation="weekly_review"))
        record_model_run(
            self.db,
            user_id=user_id,
            operation="weekly_review",
            provider=self.settings.model_provider,
            model=getattr(chat, "model", self.settings.default_chat_model),
            prompt_version=prompt_version(prompt_name),
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            estimated_cost_fen=result.usage.estimated_cost_fen,
            latency_ms=(result.raw or {}).get("latency_ms", 0),
        )
        await self.db.commit()

        parsed, error = parse_structured(result.content, WeeklyReviewNarrative)
        if error is not None:
            repair = await chat.generate(
                ChatRequest(
                    messages=messages + [ChatMessage(role="user", content=build_repair_prompt(load_prompt(prompt_name), result.content, error))],
                    operation="weekly_review_repair",
                )
            )
            parsed, error = parse_structured(repair.content, WeeklyReviewNarrative)

        if error is not None:
            # Statistics stay; narrative falls back to a fixed note
            return {
                "narrative_markdown": "统计已生成，但模型解释未通过校验，以下为原始统计。\n\n"
                + json.dumps(statistics, ensure_ascii=False, indent=2)[:2000]
            }
        return parsed.model_dump()

    async def list_reviews(self, user_id: UUID, *, limit: int = 30) -> list[WeeklyReview]:
        result = await self.db.execute(
            select(WeeklyReview)
            .where(WeeklyReview.user_id == user_id)
            .order_by(WeeklyReview.week_start.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_review(self, review_id: UUID, user_id: UUID) -> WeeklyReview | None:
        review = await self.db.get(WeeklyReview, review_id)
        if review is None or review.user_id != user_id:
            return None
        return review

    async def regenerate(self, review_id: UUID, user_id: UUID) -> WeeklyReview:
        """Regenerate a stale review at the current data revision."""
        review = await self.get_review(review_id, user_id)
        if review is None:
            raise ApiError(ErrorCode.NOT_FOUND, "复盘不存在")

        from app.services.planning import get_user_state

        state = await get_user_state(self.db, user_id)
        fresh = await self._generate(user_id, review.week_start, state.planning_revision)
        review.stale = True
        await self.db.commit()
        return fresh
