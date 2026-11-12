"""
Knowledge service (plan §7.7 / §7.10)

Import pipeline: upload+verify → hash → source metadata → subtitles or
audio extract → submit transcription → save external task id → poll →
download immediately → keep original transcript → chunk → review →
index → publish active revision.

Temporary media (original video/audio) expire after 7 days; subtitles,
transcripts and metadata are durable.
"""

import hashlib
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, ErrorCode
from app.config import get_settings
from app.db.models.knowledge import Asset, KnowledgeChunk, KnowledgeSource, SourceRevision
from app.jobs.queue import enqueue_job
from app.media.validation import classify, validate_size
from app.storage import get_storage

TEMP_RETENTION_DAYS = 7


class KnowledgeService:
    """Knowledge ingestion and management"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    # ------------------------------------------------------------------
    # Assets & uploads
    # ------------------------------------------------------------------

    async def create_upload(self, user_id: UUID, filename: str, content_type: str, byte_size: int) -> tuple[Asset, dict]:
        """Create a restricted upload grant (plan §9.4)."""
        kind = classify(filename, content_type, max_video_mb=self.settings.max_video_size_mb, max_text_mb=self.settings.max_text_size_mb)
        if kind is None:
            raise ApiError(ErrorCode.VALIDATION_ERROR, f"不支持的文件类型: {filename}")

        size_error = validate_size(kind, byte_size)
        if size_error:
            raise ApiError(ErrorCode.VALIDATION_ERROR, size_error)

        asset_id = uuid4()
        object_key = f"uploads/{user_id}/{asset_id}/{hashlib.sha256(filename.encode()).hexdigest()[:12]}{kind.suffix}"

        retention = "temporary_import" if kind.kind in ("video", "audio") else "durable"
        expires_at = (
            datetime.now(tz=None) + timedelta(days=TEMP_RETENTION_DAYS)
            if retention == "temporary_import"
            else None
        )

        asset = Asset(
            id=asset_id,
            owner_user_id=user_id,
            object_key=object_key,
            sha256="pending",
            mime_type=content_type,
            byte_size=byte_size,
            retention_class=retention,
            status="pending",
            expires_at=expires_at,
        )
        self.db.add(asset)

        storage = get_storage()
        grant = await storage.grant_upload(
            object_key,
            content_type=content_type,
            max_size_bytes=kind.max_bytes,
        )
        await self.db.commit()
        return asset, {
            "url": grant.url,
            "method": grant.method,
            "headers": grant.headers,
            "expires_at": grant.expires_at,
            "max_size_bytes": grant.max_size_bytes,
        }

    async def complete_upload(
        self, user_id: UUID, asset_id: UUID, sha256: str
    ) -> tuple[bool, int | None, str | None]:
        """Verify actual stored content: size, type, hash (plan §9.4)."""
        asset = await self.db.get(Asset, asset_id)
        if asset is None or asset.owner_user_id != user_id:
            raise ApiError(ErrorCode.NOT_FOUND, "资产不存在")

        storage = get_storage()
        try:
            data = await storage.get(asset.object_key)
        except FileNotFoundError:
            return False, None, "上传内容不存在"

        actual_size = len(data)
        if actual_size != asset.byte_size:
            return False, actual_size, "文件大小与声明不符"

        actual_hash = hashlib.sha256(data).hexdigest()
        if actual_hash != sha256:
            return False, actual_size, "内容哈希不匹配"

        asset.sha256 = actual_hash
        asset.status = "verified"
        await self.db.commit()
        return True, actual_size, None

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    async def create_import(
        self,
        user_id: UUID,
        asset_id: UUID,
        *,
        title: str,
        author: str | None,
        original_url: str | None,
    ) -> tuple[UUID, UUID]:
        """Create source + import job from one of my verified assets."""
        asset = await self.db.get(Asset, asset_id)
        if asset is None or asset.owner_user_id != user_id:
            raise ApiError(ErrorCode.NOT_FOUND, "资产不存在")
        if asset.status != "verified":
            raise ApiError(ErrorCode.DEPENDENCY_PENDING, "资产尚未通过上传校验")

        key = asset.object_key.lower()
        if key.endswith(".mp4"):
            kind = "video"
        elif key.endswith((".mp3", ".m4a", ".wav")):
            kind = "audio"
        elif key.endswith((".srt", ".vtt")):
            kind = "subtitle"
        else:
            kind = "document"

        source = KnowledgeSource(
            owner_user_id=user_id,
            visibility="private",  # default private (plan §5.7)
            title=title,
            author=author,
            original_url=original_url,
            source_type=kind,
            status="processing",
        )
        self.db.add(source)
        await self.db.flush()

        job = await enqueue_job(
            self.db,
            job_type="knowledge_import",
            owner_user_id=user_id,
            payload={
                "source_id": str(source.id),
                "asset_id": str(asset_id),
                "object_key": asset.object_key,
            },
            dedupe_key=f"knowledge_import:{source.id}",
        )
        await self.db.commit()
        return job.id, source.id

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def list_sources(self, user_id: UUID, *, limit: int = 30, cursor: str | None = None):
        """Sources I can access: shared + my own."""
        query = (
            select(KnowledgeSource)
            .where(
                (KnowledgeSource.visibility == "shared")
                | (KnowledgeSource.owner_user_id == user_id)
            )
            .order_by(KnowledgeSource.updated_at.desc())
            .limit(limit + 1)
        )
        if cursor:
            query = query.where(KnowledgeSource.id > UUID(cursor))

        result = await self.db.execute(query)
        rows = list(result.scalars().all())
        next_cursor = str(rows[-1].id) if len(rows) > limit else None
        return rows[:limit], next_cursor

    async def source_detail(self, source_id: UUID) -> dict:
        source = await self.db.get(KnowledgeSource, source_id)
        if source is None:
            raise ApiError(ErrorCode.NOT_FOUND, "来源不存在")

        revisions = (
            await self.db.execute(
                select(SourceRevision)
                .where(SourceRevision.source_id == source_id)
                .order_by(SourceRevision.revision.desc())
            )
        ).scalars().all()

        chunks: list[KnowledgeChunk] = []
        if source.active_revision_id is not None:
            chunks = (
                await self.db.execute(
                    select(KnowledgeChunk)
                    .where(KnowledgeChunk.source_revision_id == source.active_revision_id)
                    .order_by(KnowledgeChunk.ordinal)
                )
            ).scalars().all()

        return {"source": source, "revisions": list(revisions), "chunks": list(chunks)}

    # ------------------------------------------------------------------
    # Revisions: edit → new revision; approve → indexing → ready
    # ------------------------------------------------------------------

    async def create_revision_with_corrections(
        self, source: KnowledgeSource, corrected_chunks: list[dict]
    ) -> SourceRevision:
        """Editing published subtitles creates a NEW revision (plan §7.10)."""
        latest = (
            await self.db.execute(
                select(SourceRevision)
                .where(SourceRevision.source_id == source.id)
                .order_by(SourceRevision.revision.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        next_revision = (latest.revision + 1) if latest else 1

        canonical = hashlib.sha256(
            "\n".join(
                f"{c.get('ordinal')}:{c.get('corrected_text', '')}" for c in corrected_chunks
            ).encode("utf-8")
        ).hexdigest()

        revision = SourceRevision(
            source_id=source.id,
            revision=next_revision,
            content_hash=canonical,
            status="awaiting_review",
        )
        self.db.add(revision)
        source.status = "awaiting_review"
        await self.db.commit()
        await self.db.refresh(revision)
        return revision

    async def approve_revision(self, revision_id: UUID, reviewer_id: UUID) -> KnowledgeSource:
        """Approve → indexing job → (on success) active revision flips."""
        revision = await self.db.get(SourceRevision, revision_id)
        if revision is None:
            raise ApiError(ErrorCode.NOT_FOUND, "修订不存在")
        if revision.status not in ("awaiting_review",):
            raise ApiError(ErrorCode.VALIDATION_ERROR, "修订状态不允许审核")

        source = await self.db.get(KnowledgeSource, revision.source_id)
        revision.reviewed_by = reviewer_id
        revision.reviewed_at = datetime.now(tz=None)
        revision.status = "indexing"
        source.status = "indexing"
        await self.db.commit()

        await enqueue_job(
            self.db,
            job_type="knowledge_index",
            owner_user_id=source.owner_user_id,
            payload={"revision_id": str(revision.id)},
            dedupe_key=f"knowledge_index:{revision.id}",
        )
        await self.db.commit()
        return source

    async def share_source(self, source_id: UUID, admin_id: UUID) -> KnowledgeSource:
        """Admin publishes a source to the shared library."""
        source = await self.db.get(KnowledgeSource, source_id)
        if source is None:
            raise ApiError(ErrorCode.NOT_FOUND, "来源不存在")
        if source.status != "ready":
            raise ApiError(ErrorCode.DEPENDENCY_PENDING, "来源尚未就绪，无法共享")
        source.visibility = "shared"
        await self.db.commit()
        return source

    async def withdraw_source(self, source_id: UUID, user_id: UUID, *, is_admin: bool) -> KnowledgeSource:
        """Withdraw: excluded from new retrievals immediately."""
        source = await self.db.get(KnowledgeSource, source_id)
        if source is None:
            raise ApiError(ErrorCode.NOT_FOUND, "来源不存在")
        if not is_admin and source.owner_user_id != user_id:
            raise ApiError(ErrorCode.NOT_FOUND, "来源不存在")
        source.status = "withdrawn"
        await self.db.commit()
        return source
