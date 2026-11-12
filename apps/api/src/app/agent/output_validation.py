"""
Output validation (plan §4.4)

Three layers: Pydantic structure, citation validation, domain business
validation. One repair attempt with explicit errors; repair never
widens the task scope.
"""

import json
import logging
from uuid import UUID

from pydantic import BaseModel, ValidationError

from app.providers.errors import ProviderError
from app.providers.qwen_chat import parse_json_content
from app.rag.citations import CitationCheck, validate_citations

logger = logging.getLogger(__name__)

MAX_REPAIR_ATTEMPTS = 1


def parse_structured[T: BaseModel](content: str, model_cls: type[T]) -> tuple[T | None, str | None]:
    """Parse + structurally validate; returns (parsed, error_message)."""
    try:
        parsed_json = parse_json_content(content)
    except ProviderError as exc:
        return None, f"JSON 解析失败: {exc.message}"
    try:
        return model_cls.model_validate(parsed_json), None
    except ValidationError as exc:
        errors = "; ".join(
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()[:8]
        )
        return None, f"结构校验失败: {errors}"


async def check_citations(
    db,
    user_id: UUID,
    retrieved_chunk_ids: list[UUID],
    answer_citations: list,
) -> str | None:
    """Validate citations belong to this retrieval; returns error or None."""
    cited_ids = [str(c.get("chunk_id") if isinstance(c, dict) else c) for c in answer_citations if c]
    checks: list[CitationCheck] = await validate_citations(db, user_id, retrieved_chunk_ids, cited_ids)
    invalid = [c for c in checks if not c.valid]
    if invalid:
        reasons = "; ".join(f"{c.cited_id}({c.reason})" for c in invalid[:5])
        return f"引用校验失败: {reasons}"
    return None


def build_repair_prompt(task_prompt: str, original_output: str, error: str) -> str:
    """repair_output.md payload: fix exactly the reported errors."""
    return (
        "以下输出未通过校验。请只修复报告的错误，不要改变任务范围，"
        "不要新增或删除字段，不要编造新引用。\n\n"
        f"## 原始任务\n{task_prompt}\n\n"
        f"## 原始输出\n{original_output}\n\n"
        f"## 校验错误\n{error}\n"
    )


def safe_json_default(obj):
    if isinstance(obj, UUID):
        return str(obj)
    return str(obj)


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=safe_json_default)


def validate_proposed_actions(actions: list[dict], allowed_ids: dict[str, list[str]]) -> str | None:
    """proposed_actions may only reference backend-generated legal ids
    with the four allowed action types (plan §6.5)."""
    allowed_types = {"review_workout_draft", "review_memory_candidate", "review_plan_draft", "open_source"}
    for action in actions:
        action_type = action.get("type")
        if action_type not in allowed_types:
            return f"不允许的操作类型: {action_type}"
        entity_key = {
            "review_workout_draft": "draft_id",
            "review_memory_candidate": "candidate_id",
            "review_plan_draft": "plan_id",
            "open_source": "source_id",
        }.get(action_type)
        entity_id = action.get(entity_key)
        if not entity_id:
            return f"操作 {action_type} 缺少 {entity_key}"
        legal = allowed_ids.get(action_type, [])
        if str(entity_id) not in [str(x) for x in legal]:
            return f"操作 {action_type} 引用了不合法的实体 {entity_id}"
    return None
