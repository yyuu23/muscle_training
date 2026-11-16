"""
External submission with unknown outcome (plan §9.1 / §12.2): when a
transcription submit result is UNKNOWN (request sent, no task id), the
job must land in needs_attention — never a blind resubmit that could
double-charge.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.db.models.knowledge import Asset, KnowledgeSource
from app.db.models.operations import Job
from app.providers.fake import FakeTranscriptionProvider, FaultInjection

pytestmark = pytest.mark.integration


class _StubStorage:
    """Just enough storage for the import handler to reach submit()."""

    async def get(self, object_key: str) -> bytes:
        return b"fake-audio-bytes"

    async def grant_download(self, object_key: str, expires_seconds: int):
        class _Grant:
            url = f"stub://{object_key}"

        return _Grant()


async def test_unknown_submit_lands_in_needs_attention(db, monkeypatch):
    import app.jobs.handlers.import_knowledge as handler_mod
    from app.db.models.auth import User
    from app.utils.password import hash_password

    owner = User(
        id=uuid.uuid4(),
        username_normalized=f"u-{uuid.uuid4().hex[:10]}",
        display_name="owner",
        password_hash=hash_password("owner-password-123"),
        role="member",
        status="active",
    )
    db.add(owner)
    await db.flush()

    source = KnowledgeSource(
        id=uuid.uuid4(), owner_user_id=owner.id, visibility="private",
        title="音频资料", source_type="audio", status="processing",
    )
    object_key = f"tmp/{uuid.uuid4().hex}.m4a"
    asset = Asset(
        id=uuid.uuid4(), owner_user_id=owner.id, object_key=object_key,
        sha256="0" * 64, mime_type="audio/mp4", byte_size=128,
        retention_class="temporary_import", status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db.add_all([source, asset])

    job = Job(
        id=uuid.uuid4(),
        owner_user_id=owner.id,
        type="knowledge_import",
        status="running",
        payload={"source_id": str(source.id), "asset_id": str(asset.id), "object_key": object_key},
        attempts=1,
        max_attempts=3,
        run_after=datetime.now(UTC) - timedelta(seconds=1),
    )
    db.add(job)
    await db.commit()

    # Fault-injected fake provider: submit outcome UNKNOWN.
    fake = FakeTranscriptionProvider(faults=FaultInjection(transcription_submit_unknown=True))
    monkeypatch.setattr(handler_mod, "get_transcription_provider", lambda: fake)
    monkeypatch.setattr(handler_mod, "get_storage", lambda: _StubStorage())

    await handler_mod.handle_import(db, job)

    refreshed = await db.get(Job, job.id)
    assert refreshed.status == "needs_attention"
    assert refreshed.error_code == "SUBMISSION_UNKNOWN"
    # Crucially: NO external task id was recorded → nothing to resume,
    # and the provider saw exactly one submit (no blind double-submit).
    assert refreshed.external_task_id is None
    assert fake.tasks == {}

    # The source is marked failed rather than stuck in processing.
    refreshed_source = await db.get(KnowledgeSource, source.id)
    assert refreshed_source.status == "failed"
