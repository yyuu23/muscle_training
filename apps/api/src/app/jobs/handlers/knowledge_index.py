"""
Knowledge indexing handler (plan §7.10 / indexing.py)

Approved revision → chunk → embed → atomic flip to active+ready.
Model/dimension consistency is verified before switching.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge import SourceRevision
from app.jobs.queue import complete_job, fail_job
from app.rag.indexing import activate_revision, index_revision, verify_model_consistency

logger = logging.getLogger(__name__)


async def handle_knowledge_index(db: AsyncSession, job) -> None:
    revision_id = UUID(job.payload["revision_id"])

    revision = await db.get(SourceRevision, revision_id)
    if revision is None:
        await fail_job(db, job.id, error_code="REVISION_MISSING", retryable=False)
        return

    payload = revision.content_payload or {}
    segments = payload.get("segments")
    document_text = payload.get("document_text")

    try:
        consistency_error = await verify_model_consistency(db)
        if consistency_error:
            await fail_job(db, job.id, error_code="EMBEDDING_MODEL_MISMATCH", error_detail=consistency_error, retryable=False)
            return

        count = await index_revision(
            db,
            revision_id,
            segments=segments,
            document_text=document_text,
        )
        if count == 0:
            await fail_job(db, job.id, error_code="NO_CHUNKS", retryable=False)
            return

        await activate_revision(db, revision.source_id, revision_id)
        await complete_job(db, job.id, {"chunks_indexed": count})
    except Exception as exc:  # noqa: BLE001
        logger.exception("indexing failed")
        await fail_job(db, job.id, error_code="INDEX_ERROR", error_detail=str(exc)[:500])
