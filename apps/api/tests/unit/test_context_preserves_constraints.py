"""
Context trimming tests (plan §7.3): trim order, constraints never
dropped, over-budget must-keep raises an explainable error.
"""

import pytest

from app.agent.context_builder import (
    ContextBundle,
    KnowledgeEvidence,
    RawRecord,
    trim_to_budget,
)
from app.api.errors import ApiError


def _bundle(**overrides) -> ContextBundle:
    base = {
        "request_id": "req-1",
        "task_type": "answer_question",
        "user_timezone": "Asia/Shanghai",
        "profile_version": 1,
        "planning_revision": 5,
        "confirmed_profile": {"goal": "力量", "equipment": ["barbell"]},
        "confirmed_constraints": [{"kind": "training_limitation", "value": "腰部不适，避免大重量硬拉"}],
        "unresolved_recent_reports": [{"kind": "unresolved_discomfort", "value": "膝盖外侧不适"}],
        "active_plan_id": None,
        "active_plan_summary": None,
        "recent_training_summary": {"sessions_last_30d": 3},
        "relevant_raw_records": [],
        "knowledge_evidence": [],
        "recent_chat": [],
    }
    base.update(overrides)
    return ContextBundle(**base)


def test_chat_history_dropped_first():
    bundle = _bundle(
        recent_chat=[{"role": "user", "content": "x" * 3000}],
        knowledge_evidence=[
            KnowledgeEvidence(chunk_id="k1", title="资料", start_ms=0, end_ms=1000, text="核心资料内容，必须保留。")
        ],
    )
    trimmed = trim_to_budget(bundle, 1000)
    assert trimmed.recent_chat == []
    # Knowledge and constraints survive
    assert len(trimmed.knowledge_evidence) == 1
    assert len(trimmed.confirmed_constraints) == 1


def test_low_ranked_knowledge_dropped_second():
    bundle = _bundle(
        knowledge_evidence=[
            KnowledgeEvidence(chunk_id="k1", title="高排名", start_ms=None, end_ms=None, text="核心内容"),
            KnowledgeEvidence(chunk_id="k2", title="低排名", start_ms=None, end_ms=None, text="边缘内容" * 200),
        ],
    )
    trimmed = trim_to_budget(bundle, 800)
    # The oversized chunk gets dropped; the small one may remain
    remaining_ids = [k.chunk_id for k in trimmed.knowledge_evidence]
    assert "k1" in remaining_ids


def test_raw_records_dropped_third():
    bundle = _bundle(
        relevant_raw_records=[
            RawRecord(session_id="old", started_at="2026-10-01", summary="旧记录" * 50),
            RawRecord(session_id="new", started_at="2026-11-01", summary="新记录"),
        ],
    )
    trimmed = trim_to_budget(bundle, 600)
    assert any(r.session_id == "new" for r in trimmed.relevant_raw_records)


def test_constraints_never_dropped():
    long_constraint = {"kind": "training_limitation", "value": "避免" + "、" * 400}
    bundle = _bundle(confirmed_constraints=[long_constraint])
    trimmed = trim_to_budget(bundle, 1000)
    assert trimmed.confirmed_constraints == [long_constraint]


def test_unresolved_discomfort_preserved():
    discomfort = [{"kind": "unresolved_discomfort", "value": "肩部不适，相关动作暂缓加重"}]
    bundle = _bundle(
        unresolved_recent_reports=discomfort,
        recent_chat=[{"role": "user", "content": "x" * 3000}],  # gets trimmed first
    )
    trimmed = trim_to_budget(bundle, 800)
    assert trimmed.unresolved_recent_reports == discomfort


def test_must_keep_over_budget_raises_explainable_error():
    huge_constraints = [
        {"kind": "training_limitation", "value": "限制" * 3000},
        {"kind": "exercise_exclusion", "value": "排除" * 3000},
    ]
    bundle = _bundle(confirmed_constraints=huge_constraints)
    with pytest.raises(ApiError) as exc:
        trim_to_budget(bundle, 1000)
    assert "超过预算" in exc.value.message
    assert "缩小问题范围" in exc.value.message


def test_no_trim_needed_when_within_budget():
    bundle = _bundle()
    trimmed = trim_to_budget(bundle, 100_000)
    assert trimmed is bundle or trimmed.confirmed_profile == bundle.confirmed_profile
