"""
Knowledge import job handler (plan §7.7)

Pipeline: subtitles or audio extract → submit transcription → save
external task id → reschedule polling (waiting_external, no DB tx
held) → download result immediately → keep original transcript →
chunk → awaiting_review.

Restart with a known external task id resumes polling; unknown submit
outcomes go to needs_attention (never a blind resubmit).
"""

import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge import Asset, KnowledgeSource, SourceRevision
from app.jobs.queue import complete_job, defer_job, fail_job
from app.media.audio_extract import cleanup_temp_dir, extract_audio, job_temp_dir, probe
from app.media.subtitles import parse_subtitles
from app.providers import get_transcription_provider
from app.providers.errors import ProviderError
from app.storage import get_storage

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30
MAX_POLL_MINUTES = 60


async def handle_import(db: AsyncSession, job) -> None:
    """Run/continue a knowledge import job."""
    payload = job.payload
    source_id = UUID(payload["source_id"])
    asset_id = UUID(payload["asset_id"])
    object_key = payload["object_key"]

    source = await db.get(KnowledgeSource, source_id)
    asset = await db.get(Asset, asset_id)
    if source is None or asset is None:
        await fail_job(db, job.id, error_code="ENTITY_MISSING", retryable=False)
        return

    storage = get_storage()

    # Resume an existing external transcription task
    if job.external_task_id and job.status == "waiting_external":
        await _resume_transcription(db, job, source)
        return

    try:
        data = await storage.get(object_key)
    except FileNotFoundError:
        await fail_job(db, job.id, error_code="ASSET_MISSING", error_detail="上传对象已过期或删除", retryable=False)
        source.status = "failed"
        await db.commit()
        return

    suffix = Path(object_key).suffix.lower()

    if suffix in (".srt", ".vtt"):
        # Subtitle files: parse directly, no transcription
        cues = parse_subtitles(data.decode("utf-8", errors="replace"), suffix)
        if not cues:
            await fail_job(db, job.id, error_code="EMPTY_SUBTITLE", retryable=False)
            source.status = "failed"
            await db.commit()
            return
        await _create_awaiting_revision(
            db, source, asset,
            segments=[{"start_ms": c.start_ms, "end_ms": c.end_ms, "text": c.text} for c in cues],
        )
        await complete_job(db, job.id, {"revision_created": True})
        return

    if suffix in (".txt", ".md"):
        text = data.decode("utf-8", errors="replace")
        await _create_awaiting_revision(db, source, asset, document_text=text)
        await complete_job(db, job.id, {"revision_created": True})
        return

    # Video/audio: extract audio if needed, then transcribe
    temp_dir = job_temp_dir(str(job.id))
    try:
        audio_key = object_key
        if suffix == ".mp4":
            local_input = temp_dir / "input.mp4"
            local_input.write_bytes(data)
            probe_result = await probe(local_input)
            if not probe_result.has_audio:
                await fail_job(db, job.id, error_code="NO_AUDIO", retryable=False)
                source.status = "failed"
                await db.commit()
                return
            audio_path = temp_dir / "audio.m4a"
            await extract_audio(local_input, audio_path)
            audio_bytes = audio_path.read_bytes()
            audio_object_key = f"transcode/{job.id}/audio.m4a"
            await storage.put(audio_object_key, audio_bytes, "audio/mp4")
            audio_asset = Asset(
                owner_user_id=asset.owner_user_id,
                object_key=audio_object_key,
                sha256=hashlib.sha256(audio_bytes).hexdigest(),
                mime_type="audio/mp4",
                byte_size=len(audio_bytes),
                retention_class="temporary_import",
                status="verified",
                expires_at=datetime.now(tz=None) + timedelta(days=7),
            )
            db.add(audio_asset)
            await db.commit()
            audio_key = audio_object_key
            data = audio_bytes

        # Grant a read URL for the transcription service
        grant = await storage.grant_download(audio_key, expires_seconds=3600)
        provider = get_transcription_provider()
        external = await provider.submit(grant.url, file_name=Path(audio_key).name)

        job.external_task_id = external.task_id
        await defer_job(
            db,
            job.id,
            run_after=datetime.now(tz=None) + timedelta(seconds=POLL_INTERVAL_SECONDS),
            external_task_id=external.task_id,
            phase="transcription_polling",
        )
        source.status = "processing"
        await db.commit()
    except ProviderError as exc:
        if exc.code == "SUBMISSION_UNKNOWN":
            # Unknown outcome without a task id → needs_attention (plan §9.1)
            await fail_job(db, job.id, error_code="SUBMISSION_UNKNOWN", error_detail=exc.message, retryable=False)
            source.status = "failed"
            await db.commit()
            return
        await fail_job(db, job.id, error_code=exc.code, error_detail=exc.message, retryable=exc.retryable)
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("import failed")
        await fail_job(db, job.id, error_code="IMPORT_ERROR", error_detail=str(exc)[:500])
        return
    finally:
        cleanup_temp_dir(temp_dir)


async def _resume_transcription(db: AsyncSession, job, source: KnowledgeSource) -> None:
    """Poll the external task; download + chunk on success."""
    provider = get_transcription_provider()
    try:
        external = await provider.poll(job.external_task_id)
    except ProviderError as exc:
        await fail_job(db, job.id, error_code=exc.code, error_detail=exc.message, retryable=exc.retryable)
        return

    if external.status == "running":
        await defer_job(
            db,
            job.id,
            run_after=datetime.now(tz=None) + timedelta(seconds=POLL_INTERVAL_SECONDS),
        )
        return
    if external.status == "unknown":
        await fail_job(db, job.id, error_code="EXTERNAL_TASK_LOST", retryable=False)
        source.status = "failed"
        await db.commit()
        return
    if external.status == "failed":
        await fail_job(db, job.id, error_code="TRANSCRIPTION_FAILED", retryable=False)
        source.status = "failed"
        await db.commit()
        return

    # Succeeded: download immediately (short-lived URL), keep original
    transcript = await provider.fetch_result(external.result_url)

    # Persist the raw transcript as a durable asset
    import json

    storage = get_storage()
    raw_json = json.dumps(transcript.raw or {}, ensure_ascii=False).encode("utf-8")
    raw_key = f"transcripts/{source.id}/original.json"
    await storage.put(raw_key, raw_json, "application/json")

    segments = [
        {"start_ms": s.start_ms, "end_ms": s.end_ms, "text": s.text}
        for s in transcript.segments
    ]
    if not segments:
        await fail_job(db, job.id, error_code="EMPTY_TRANSCRIPT", retryable=False)
        source.status = "failed"
        await db.commit()
        return

    await _create_awaiting_revision(db, source, None, segments=segments, transcript_key=raw_key)
    await complete_job(db, job.id, {"revision_created": True, "transcript_key": raw_key})


async def _create_awaiting_revision(
    db: AsyncSession,
    source: KnowledgeSource,
    asset: Asset | None,
    *,
    segments: list[dict] | None = None,
    document_text: str | None = None,
    transcript_key: str | None = None,
) -> SourceRevision:
    """Create revision 1 in awaiting_review with content hash."""
    canonical_source = segments if segments is not None else document_text or ""
    content_hash = hashlib.sha256(str(canonical_source).encode("utf-8")).hexdigest()

    revision = SourceRevision(
        source_id=source.id,
        revision=1,
        content_hash=content_hash,
        status="awaiting_review",
        content_payload={
            "segments": segments,
            "document_text": document_text,
            "transcript_key": transcript_key,
        },
    )
    db.add(revision)
    source.status = "awaiting_review"
    await db.commit()
    return revision
