"""
Agent limits and budget (plan §7.1 / §11.4)

Interactive: ≤3 model calls, ≤6 tool calls, 60s, ~12K input tokens.
Background plan generation: 1 generate + ≤1 repair, 180s total.
Restarts never reset model-call budgets (tracked in DB, not memory).
Budget: reserve before call, settle after; retries also count.
"""

import time
from dataclasses import field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, ErrorCode
from app.config import get_settings
from app.db.models.operations import ModelRun


class BudgetTracker:
    """Per-request budget: model calls, tool calls, wall clock, tokens."""

    def __init__(
        self,
        *,
        max_model_calls: int | None = None,
        max_tool_calls: int | None = None,
        timeout_seconds: int | None = None,
        max_context_tokens: int | None = None,
    ):
        settings = get_settings()
        self.max_model_calls = max_model_calls if max_model_calls is not None else settings.max_agent_model_calls
        self.max_tool_calls = max_tool_calls if max_tool_calls is not None else settings.max_agent_tool_calls
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.interactive_timeout_seconds
        self.max_context_tokens = max_context_tokens or settings.max_context_tokens

        self.model_calls = 0
        self.tool_calls = 0
        self.estimated_tokens = 0
        self.started_at = time.monotonic()
        self.reserved_cost_fen = 0
        self.events: list[str] = field(default_factory=list)

    def check_model_call(self) -> None:
        if self.model_calls >= self.max_model_calls:
            raise ApiError(
                ErrorCode.BUDGET_EXHAUSTED,
                f"已达到单次交互模型调用上限（{self.max_model_calls} 次）",
            )

    def record_model_call(self, *, input_tokens: int, output_tokens: int, cost_fen: int = 0) -> None:
        self.model_calls += 1
        self.estimated_tokens += input_tokens + output_tokens
        self.reserved_cost_fen += cost_fen

    def check_tool_call(self) -> None:
        if self.tool_calls >= self.max_tool_calls:
            raise ApiError(
                ErrorCode.BUDGET_EXHAUSTED,
                f"已达到工具调用上限（{self.max_tool_calls} 次）",
            )

    def record_tool_call(self) -> None:
        self.tool_calls += 1

    def check_timeout(self) -> None:
        elapsed = time.monotonic() - self.started_at
        if elapsed > self.timeout_seconds:
            raise ApiError(
                ErrorCode.MODEL_UNAVAILABLE,
                f"交互超过时间预算（{self.timeout_seconds} 秒）",
            )

    def remaining_seconds(self) -> float:
        return max(0.0, self.timeout_seconds - (time.monotonic() - self.started_at))


async def monthly_spend_fen(db: AsyncSession) -> int:
    """Sum estimated costs for the current month across all runs."""
    from datetime import datetime

    now = datetime.now(tz=None)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.coalesce(func.sum(ModelRun.estimated_cost), 0)).where(
            ModelRun.created_at >= month_start
        )
    )
    return int(result.scalar() or 0)


async def check_monthly_budget(db: AsyncSession) -> tuple[bool, bool]:
    """Returns (within_budget, warning_threshold_reached)."""
    settings = get_settings()
    spent_fen = await monthly_spend_fen(db)
    budget_fen = int(settings.monthly_ai_budget_cny * 100)
    if spent_fen >= budget_fen:
        return False, True
    return True, spent_fen >= budget_fen * settings.model_budget_warning_threshold


async def reserve_budget(db: AsyncSession, estimated_fen: int) -> None:
    """Reserve before a call: hard-stop when the budget is exhausted.

    estimated_fen is the projected cost; actual usage is settled after
    the call returns (plan §11.4).
    """
    within_budget, _ = await check_monthly_budget(db)
    if not within_budget:
        raise ApiError(
            ErrorCode.BUDGET_EXHAUSTED,
            "本月 AI 预算已用完；查看、记录、同步和导出功能不受影响",
        )


def record_model_run(
    db: AsyncSession,
    *,
    user_id,
    operation: str,
    provider: str,
    model: str,
    prompt_version: str,
    input_tokens: int,
    output_tokens: int,
    estimated_cost_fen: int,
    latency_ms: int,
    status: str = "succeeded",
    error_code: str | None = None,
):
    """Persist a ModelRun row (budget + audit trail)."""
    run = ModelRun(
        user_id=user_id,
        operation=operation,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost=estimated_cost_fen,
        latency_ms=latency_ms,
        status=status,
        error_code=error_code,
    )
    db.add(run)
    return run
