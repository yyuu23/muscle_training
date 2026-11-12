"""
Agent call limit tests (plan §7.1): model/tool/time budgets, monthly
budget reserve, retries count.
"""

import pytest

from app.agent.limits import BudgetTracker
from app.api.errors import ApiError, ErrorCode


def test_model_call_limit_enforced():
    tracker = BudgetTracker(max_model_calls=3)
    for _ in range(3):
        tracker.check_model_call()
        tracker.record_model_call(input_tokens=100, output_tokens=50)
    with pytest.raises(ApiError) as exc:
        tracker.check_model_call()
    assert exc.value.code == ErrorCode.BUDGET_EXHAUSTED


def test_tool_call_limit_enforced():
    tracker = BudgetTracker(max_tool_calls=2)
    tracker.check_tool_call()
    tracker.record_tool_call()
    tracker.check_tool_call()
    tracker.record_tool_call()
    with pytest.raises(ApiError):
        tracker.check_tool_call()


def test_retries_count_toward_budget():
    """Retries also count against calls and budget (plan §11.4)."""
    tracker = BudgetTracker(max_model_calls=2)
    tracker.check_model_call()
    tracker.record_model_call(input_tokens=10, output_tokens=5, cost_fen=2)
    tracker.check_model_call()
    tracker.record_model_call(input_tokens=10, output_tokens=5, cost_fen=2)
    assert tracker.model_calls == 2
    with pytest.raises(ApiError):
        tracker.check_model_call()


def test_timeout_budget(monkeypatch):
    tracker = BudgetTracker(timeout_seconds=1)
    monkeypatch.setattr("app.agent.limits.time.monotonic", lambda: tracker.started_at + 2)
    with pytest.raises(ApiError) as exc:
        tracker.check_timeout()
    assert "时间预算" in exc.value.message


def test_remaining_seconds_never_negative():
    tracker = BudgetTracker(timeout_seconds=5)
    assert tracker.remaining_seconds() <= 5


@pytest.mark.asyncio
async def test_reserve_budget_blocks_when_exhausted():
    from unittest.mock import AsyncMock

    from app.agent.limits import reserve_budget

    class Result:
        def __init__(self, value):
            self._value = value

        def scalar(self):
            return self._value

    db = AsyncMock()
    db.execute = AsyncMock(return_value=Result(10_000_000))  # 100k CNY in fen

    with pytest.raises(ApiError) as exc:
        await reserve_budget(db, 10)
    assert exc.value.code == ErrorCode.BUDGET_EXHAUSTED
    assert "不受影响" in exc.value.message


@pytest.mark.asyncio
async def test_warning_threshold_reached():
    from unittest.mock import AsyncMock

    from app.agent.limits import check_monthly_budget

    class Result:
        def __init__(self, value):
            self._value = value

        def scalar(self):
            return self._value

    db = AsyncMock()
    db.execute = AsyncMock(return_value=Result(8_100))  # 81 CNY → over 80%
    within, warning = await check_monthly_budget(db)
    assert within is True
    assert warning is True
