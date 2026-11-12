"""
Sync API router (plan §8.4)

POST /sync/events  - up to 100 events per batch, 1MB body cap
GET  /sync/snapshot - confirmed-cache refresh payload
"""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, ErrorCode, error_response
from app.db.session import get_db_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.sync.schemas import (
    SyncBatchRequest,
    SyncBatchResponse,
    SyncSnapshotResponse,
)
from app.modules.sync.service import SyncService

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_BATCH_BYTES = 1024 * 1024


@router.post("/events", response_model=SyncBatchResponse)
async def submit_events(
    request: Request,
    request_data: SyncBatchRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Apply a batch of offline events. Each event is its own transaction."""
    if len(request_data.events) > 100:
        return error_response(
            ErrorCode.VALIDATION_ERROR, "每批最多 100 条事件", status_code=400
        )

    body_size = int(request.headers.get("content-length", 0))
    if body_size > MAX_BATCH_BYTES:
        return error_response(
            ErrorCode.VALIDATION_ERROR, "批量正文超过 1MB 限制", status_code=400
        )

    service = SyncService(db)
    results = await service.apply_batch(user.id, request_data.events)
    return SyncBatchResponse(results=results)


@router.get("/snapshot", response_model=SyncSnapshotResponse)
async def get_snapshot(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Snapshot of confirmed data for offline cache refresh."""
    service = SyncService(db)
    try:
        return await service.build_snapshot(user.id)
    except Exception as exc:  # pragma: no cover
        logger.exception("snapshot build failed")
        raise ApiError(ErrorCode.VALIDATION_ERROR, f"快照生成失败: {exc}") from exc
