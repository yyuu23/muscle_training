"""
Jobs API + upload passthrough (plan §6.4):

- GET /jobs/{id}: owner sees status/phase/result_ref; anyone else gets 404
- PUT /knowledge/assets/upload/{key}: dev filesystem storage passthrough —
  only the pending asset's owner may store bytes, size capped at the
  declared byte_size; complete_upload then verifies hash end-to-end.
"""

import hashlib
import uuid

import pytest

from app.db.models.operations import Job
from app.jobs.queue import enqueue_job
from tests.integration.conftest import register_user

pytestmark = pytest.mark.integration


async def test_job_status_owner_scoped(db, http):
    # NOTE: the shared http client keeps the LAST session cookie, so the
    # second register call makes the caller the attacker, not the owner.
    owner_id, _, _ = await register_user(http, f"job-{uuid.uuid4().hex[:8]}")
    _, _, _ = await register_user(http, f"other-{uuid.uuid4().hex[:8]}")  # caller

    job = await enqueue_job(db, job_type="generate_plan", owner_user_id=owner_id, payload={})
    job_id = job.id  # capture before rollback expires the instance
    await db.rollback()  # release the fixture session so the API read sees fresh state

    me = (await http.get("/api/v1/auth/me")).json()
    assert me["user"]["id"] != str(owner_id)  # caller really is someone else

    # The caller is not the job owner → 404, never 403.
    resp = await http.get(f"/api/v1/jobs/{job_id}", headers={"Origin": "http://test"})
    assert resp.status_code == 404, resp.text

    # Unknown ids are 404 too (no information leak either way).
    resp = await http.get(f"/api/v1/jobs/{uuid.uuid4()}", headers={"Origin": "http://test"})
    assert resp.status_code == 404


async def test_job_status_returns_lifecycle_fields(db, http):
    from datetime import UTC, datetime, timedelta

    user_id, _, _ = await register_user(http, f"poll-{uuid.uuid4().hex[:8]}")
    job = Job(
        id=uuid.uuid4(),
        # register_user returns a JSON string; the model column is UUID —
        # passing the raw str keeps a str in the identity-map attribute.
        owner_user_id=uuid.UUID(user_id),
        type="generate_plan",
        status="running",
        phase="drafting",
        payload={},
        attempts=1,
        max_attempts=3,
        run_after=datetime.now(UTC) - timedelta(seconds=1),
    )
    db.add(job)
    await db.commit()
    job_id = job.id

    # Sanity: replicate the route's exact query on this session.
    from sqlalchemy import select as sa_select

    row = (await db.execute(sa_select(Job).where(Job.id == job_id))).scalar_one_or_none()
    me = (await http.get("/api/v1/auth/me")).json()
    assert row is not None, "job row vanished"
    assert str(row.owner_user_id) == str(user_id), (
        f"owner mismatch: row={row.owner_user_id!r} user_id={user_id!r}"
    )
    assert me["user"]["id"] == str(user_id), (
        f"caller mismatch: me={me['user']['id']!r} user_id={user_id!r}"
    )

    resp = await http.get(f"/api/v1/jobs/{job_id}", headers={"Origin": "http://test"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["job_id"] == str(job.id)
    assert body["status"] == "running"
    assert body["phase"] == "drafting"


async def test_upload_passthrough_full_flow(db, http):
    """create_upload → PUT grant url → complete_upload verifies hash."""
    _, csrf, _ = await register_user(http, f"up-{uuid.uuid4().hex[:8]}")

    content = b"hello knowledge import"
    resp = await http.post(
        "/api/v1/knowledge/assets/uploads",
        json={
            "filename": "notes.txt",
            "content_type": "text/plain",
            "byte_size": len(content),
        },
        headers={"Origin": "http://test", "X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["upload"]["url"].startswith("/api/v1/knowledge/assets/upload/")

    # PUT via the grant URL (exactly what the frontend must do).
    resp = await http.put(
        created["upload"]["url"],
        content=content,
        headers={
            "Origin": "http://test",
            "X-CSRF-Token": csrf,
            "Content-Type": "text/plain",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["stored_bytes"] == len(content)

    sha256 = hashlib.sha256(content).hexdigest()
    resp = await http.post(
        f"/api/v1/knowledge/assets/{created['asset_id']}/complete",
        json={"sha256": sha256},
        headers={"Origin": "http://test", "X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["verified"] is True


async def test_upload_passthrough_rejects_oversize(db, http):
    _, csrf, _ = await register_user(http, f"big-{uuid.uuid4().hex[:8]}")

    resp = await http.post(
        "/api/v1/knowledge/assets/uploads",
        json={"filename": "small.txt", "content_type": "text/plain", "byte_size": 4},
        headers={"Origin": "http://test", "X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()

    resp = await http.put(
        created["upload"]["url"],
        content=b"way-more-than-four-bytes",
        headers={"Origin": "http://test", "X-CSRF-Token": csrf, "Content-Type": "text/plain"},
    )
    assert resp.status_code == 400, resp.text
