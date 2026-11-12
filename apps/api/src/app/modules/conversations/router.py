"""
Conversations API router (plan §6.4)

POST /chat runs the controlled orchestrator; answers are validated
before returning. Plain conversation text expires after 90 days
(retention enforced by maintenance).
"""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import Orchestrator
from app.api.errors import ApiError, ErrorCode
from app.config import get_settings
from app.db.models.operations import Conversation, Message
from app.db.session import get_db_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.conversations.schemas import (
    ChatRequest,
    CoachResponseOut,
    ConversationResponse,
    DraftConfirmRequest,
    DraftConfirmResponse,
    MessageResponse,
)

router = APIRouter()


@router.post("/chat", response_model=CoachResponseOut)
async def chat(
    request_data: ChatRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Free chat with the controlled agent workflow."""
    settings = get_settings()
    if not settings.enable_agent:
        return CoachResponseOut(
            status="unable_to_answer",
            answer_markdown="模型功能未启用。",
        )
    if settings.model_provider == "qwen" and not settings.dashscope_api_key:
        return CoachResponseOut(
            status="unable_to_answer",
            answer_markdown="模型功能未配置 API 密钥；记录、查看与同步功能不受影响。",
        )

    orchestrator = Orchestrator(db, user.id)
    try:
        result = await orchestrator.handle_chat(request_data.message, request_data.conversation_id)
    except ApiError as exc:
        return CoachResponseOut(
            status="unable_to_answer",
            answer_markdown=exc.message,
            missing_fields=list(exc.details.get("missing_fields", [])),
        )

    # Extract memory candidates from the user statement (plan §7.11)
    candidate_ids: list[str] = []
    if settings.dashscope_api_key or settings.model_provider == "fake":
        try:
            candidate_ids = await orchestrator._flow_extract_memory(request_data.message)
        except ApiError:
            candidate_ids = []

    return CoachResponseOut(
        status=result.status,
        answer_markdown=result.answer_markdown,
        citations=[{"chunk_id": c.chunk_id, "quote": c.quote} for c in result.citations],
        missing_fields=result.missing_fields,
        proposed_actions=result.proposed_actions,
        data_cutoff_at=result.data_cutoff_at,
        request_id=result.request_id,
        draft_id=result.draft_id,
        plan_draft_id=result.plan_draft_id,
        memory_candidate_ids=candidate_ids,
        conversation_id=request_data.conversation_id,
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(30, ge=1, le=100),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    return [ConversationResponse.model_validate(c) for c in result.scalars().all()]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(100, ge=1, le=500),
):
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise ApiError(ErrorCode.NOT_FOUND, "会话不存在")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .where(Message.user_id == user.id)
        .order_by(Message.created_at)
        .limit(limit)
    )
    return [MessageResponse.model_validate(m) for m in result.scalars().all()]


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise ApiError(ErrorCode.NOT_FOUND, "会话不存在")
    await db.execute(delete(Message).where(Message.conversation_id == conversation_id))
    await db.delete(conversation)
    await db.commit()
    return None


@router.post("/drafts/{draft_kind}/{draft_id}/confirm", response_model=DraftConfirmResponse)
async def confirm_draft(
    draft_kind: str,
    draft_id: uuid.UUID,
    request_data: DraftConfirmRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Confirm a model-organized draft; still via normal business services."""
    if draft_kind == "memory-candidate":
        from app.modules.profiles.service import ProfileService

        if request_data.decision != "accept":
            service = ProfileService(db)
            await service.resolve_candidate(draft_id, user.id, decision="reject")
            return DraftConfirmResponse(outcome="rejected", entity_id=str(draft_id))

        service = ProfileService(db)
        candidate = await service.resolve_candidate(draft_id, user.id, decision="accept")
        return DraftConfirmResponse(
            outcome="accepted",
            entity_id=str(candidate.id),
            detail={"status": candidate.status},
        )

    raise ApiError(ErrorCode.NOT_FOUND, f"未知的草稿类型 {draft_kind}")


@router.post("/conversations/retention-sweep", status_code=204)
async def retention_sweep(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete plain conversation text older than the retention window.

    Confirmed facts keep minimal source references and survive this
    sweep (plan §9.5)."""
    settings = get_settings()
    cutoff = datetime.now(tz=None) - timedelta(days=settings.chat_retention_days)
    await db.execute(
        delete(Message).where(Message.user_id == user.id).where(Message.created_at < cutoff)
    )
    await db.commit()
    return None
