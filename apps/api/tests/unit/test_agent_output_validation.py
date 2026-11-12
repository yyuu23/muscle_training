"""
Agent output validation tests (plan §4.4): JSON parsing, structure
validation, repair prompt, proposed-action legality.
"""


from app.agent.output_validation import (
    build_repair_prompt,
    parse_structured,
    validate_proposed_actions,
)
from app.agent.schemas import CoachAnswer, IntentClassification


def test_parse_valid_json():
    parsed, error = parse_structured(
        '{"intent": "general_chat", "confidence": 0.9}', IntentClassification
    )
    assert error is None
    assert parsed.intent == "general_chat"


def test_parse_invalid_json():
    parsed, error = parse_structured("这不是 JSON", IntentClassification)
    assert parsed is None
    assert "JSON" in error


def test_parse_non_object_json():
    parsed, error = parse_structured('["array"]', IntentClassification)
    assert parsed is None
    assert "对象" in error


def test_structure_mismatch_missing_field():
    parsed, error = parse_structured('{"confidence": 0.5}', IntentClassification)
    assert parsed is None
    assert "结构校验失败" in error


def test_extra_fields_forbidden():
    """Model schemas use extra=forbid — unknown fields fail validation."""
    parsed, error = parse_structured(
        '{"intent": "general_chat", "confidence": 0.9, "evil_field": "x"}',
        IntentClassification,
    )
    assert parsed is None
    assert error is not None


def test_intent_must_be_supported():
    parsed, error = parse_structured(
        '{"intent": "delete_database", "confidence": 1.0}', IntentClassification
    )
    assert parsed is None


def test_repair_prompt_contains_task_output_and_errors():
    prompt = build_repair_prompt("任务说明…", '{"bad": true}', "引用校验失败: id 不在检索结果")
    assert "任务说明…" in prompt
    assert '{"bad": true}' in prompt
    assert "引用校验失败" in prompt
    assert "不要改变任务范围" in prompt


def test_allowed_action_types_only():
    legal = {
        "review_plan_draft": ["plan-1"],
        "open_source": ["src-1"],
    }
    assert validate_proposed_actions(
        [{"type": "review_plan_draft", "plan_id": "plan-1"}], legal
    ) is None


def test_disallowed_action_type_rejected():
    error = validate_proposed_actions(
        [{"type": "execute_sql", "sql": "DROP TABLE"}], {"open_source": []}
    )
    assert "不允许的操作类型" in error


def test_action_referencing_unknown_entity_rejected():
    error = validate_proposed_actions(
        [{"type": "review_plan_draft", "plan_id": "forged-id"}],
        {"review_plan_draft": ["real-plan"]},
    )
    assert "不合法的实体" in error


def test_action_missing_entity_id_rejected():
    error = validate_proposed_actions([{"type": "open_source"}], {"open_source": ["s"]})
    assert "缺少" in error


def test_coach_answer_citation_shape():
    parsed, error = parse_structured(
        '{"status": "answered", "answer_markdown": "回答", "citations": [{"chunk_id": "abc", "quote": "原文"}]}',
        CoachAnswer,
    )
    assert error is None
    assert parsed.citations[0].chunk_id == "abc"
