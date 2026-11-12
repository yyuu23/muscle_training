"""
Knowledge API router (plan §6.4)

- POST /assets/uploads, POST /assets/{id}/complete
- POST /knowledge/imports (202 job)
- GET /knowledge/sources, GET /knowledge/sources/{id}
- PATCH /knowledge/revisions/{id}, POST /knowledge/revisions/{id}/approve
- POST /knowledge/sources/{id}/share, POST /knowledge/sources/{id}/withdraw
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import CurrentAdminUser, CurrentUser
from app.modules.knowledge.permissions import get_readable_source, require_owner
from app.modules.knowledge.schemas import (
    ChunkResponse,
    KnowledgeImportRequest,
    KnowledgeImportResponse,
    KnowledgeSourceResponse,
    RevisionPatchRequest,
    ShareRequest,
    SourceDetailResponse,
    SourceListResponse,
    SourceRevisionResponse,
    UploadCompleteRequest,
    UploadCompleteResponse,
    UploadCreateRequest,
    UploadCreateResponse,
)
from app.modules.knowledge.service import KnowledgeService

router = APIRouter()


# ----------------------------------------------------------------------
# Assets
# ----------------------------------------------------------------------


@router.post("/assets/uploads", response_model=UploadCreateResponse, status_code=201)
async def create_upload(
    request_data: UploadCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a restricted upload; returns asset id + upload info."""
    service = KnowledgeService(db)
    asset, upload = await service.create_upload(
        user.id, request_data.filename, request_data.content_type, request_data.byte_size
    )
    return UploadCreateResponse(
        asset_id=asset.id,
        upload=upload,
        object_key=asset.object_key,
    )


@router.post("/assets/{asset_id}/complete", response_model=UploadCompleteResponse)
async def complete_upload(
    asset_id: UUID,
    request_data: UploadCompleteRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Verify actual file size/type/hash after upload."""
    service = KnowledgeService(db)
    verified, size, detail = await service.complete_upload(user.id, asset_id, request_data.sha256)
    return UploadCompleteResponse(
        asset_id=asset_id,
        verified=verified,
        byte_size=size,
        detail=detail,
    )


# ----------------------------------------------------------------------
# Imports & sources
# ----------------------------------------------------------------------


@router.post("/imports", response_model=KnowledgeImportResponse, status_code=202)
async def create_import(
    request_data: KnowledgeImportRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Create an import job from one of my assets."""
    service = KnowledgeService(db)
    job_id, source_id = await service.create_import(
        user.id,
        request_data.asset_id,
        title=request_data.title,
        author=request_data.author,
        original_url=request_data.original_url,
    )
    return KnowledgeImportResponse(job_id=job_id, source_id=source_id)


@router.get("/sources", response_model=SourceListResponse)
async def list_sources(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(30, ge=1, le=100),
    cursor: str | None = Query(None),
):
    """Sources I can access (shared + my own)."""
    service = KnowledgeService(db)
    sources, next_cursor = await service.list_sources(user.id, limit=limit, cursor=cursor)
    return SourceListResponse(
        items=[KnowledgeSourceResponse.model_validate(s) for s in sources],
        next_cursor=next_cursor,
    )


@router.get("/sources/{source_id}", response_model=SourceDetailResponse)
async def get_source(
    source_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Source with revisions, chunks and review status."""
    await get_readable_source(db, source_id, user.id)
    service = KnowledgeService(db)
    detail = await service.source_detail(source_id)
    return SourceDetailResponse(
        source=KnowledgeSourceResponse.model_validate(detail["source"]),
        revisions=[SourceRevisionResponse.model_validate(r) for r in detail["revisions"]],
        chunks=[ChunkResponse.model_validate(c) for c in detail["chunks"]],
    )


@router.patch("/revisions/{revision_id}", response_model=SourceRevisionResponse)
async def patch_revision(
    revision_id: UUID,
    request_data: RevisionPatchRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Edit not-yet-published subtitle text → creates a new revision."""
    from app.api.errors import ApiError, ErrorCode
    from app.db.models.knowledge import SourceRevision

    revision = await db.get(SourceRevision, revision_id)
    if revision is None:
        raise ApiError(ErrorCode.NOT_FOUND, "修订不存在")

    source = await require_owner(db, revision.source_id, user.id)
    service = KnowledgeService(db)
    new_revision = await service.create_revision_with_corrections(
        source, request_data.corrected_chunks
    )
    return SourceRevisionResponse.model_validate(new_revision)


@router.post("/revisions/{revision_id}/approve")
async def approve_revision(
    revision_id: UUID,
    user: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Review and enter the indexing flow (admin, plan §6.4)."""
    service = KnowledgeService(db)
    source = await service.approve_revision(revision_id, user.id)
    return {"source_id": str(source.id), "status": source.status}


@router.post("/sources/{source_id}/share")
async def share_source(
    source_id: UUID,
    request_data: ShareRequest,
    admin: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Admin publishes a source to the shared library."""
    service = KnowledgeService(db)
    source = await service.share_source(source_id, admin.id)
    return {"source_id": str(source.id), "visibility": source.visibility}


@router.post("/sources/{source_id}/withdraw", status_code=204)
async def withdraw_source(
    source_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Withdraw a source; no longer used for new answers."""
    service = KnowledgeService(db)
    await service.withdraw_source(
        source_id, user.id, is_admin=(user.role == "admin")
    )
    return None
