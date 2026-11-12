"""
Sync idempotency tests (plan §8.5 / §12.2): same id + same content
replays the first result; same id + different content conflicts;
response-loss retries never double-log sets.
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.training import WorkoutSession
from tests.integration.conftest import register_user

pytestmark = pytest.mark.integration

DEVICE = "11111111-1111-1111-1111-111111111111"


def _event(payload: dict, seq: int) -> dict:
    body = {k: v for k, v in payload.items() if k != "_type"}
    body.setdefault("client_created_at", "2026-11-11T10:00:00+08:00")
    return {
        "event_id": str(uuid.uuid4()),
        "device_id": DEVICE,
        "client_sequence": seq,
        "event_type": payload["_type"],
        "client_created_at": "2026-11-11T10:00:00+08:00",
        "payload": body,
    }


@pytest.mark.asyncio
async def test_replay_same_event_returns_already_applied(http, db: AsyncSession):
    user_id, csrf, _ = await register_user(http, f"sync-{uuid.uuid4().hex[:8]}")

    session_id = str(uuid.uuid4())
    event = _event({"_type": "workout.started", "id": session_id, "started_at": "2026-11-11T10:00:00+08:00"}, 1)

    outcomes = []
    for _ in range(2):  # response lost → client retries verbatim
        response = await http.post(
            "/api/v1/sync/events",
            json={"events": [event]},
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 200
        outcomes.append(response.json()["results"][0]["outcome"])

    assert outcomes[0] == "applied"
    assert outcomes[1] == "already_applied"

    rows = (
        await db.execute(
            select(WorkoutSession).where(WorkoutSession.user_id == uuid.UUID(user_id))
        )
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_same_id_different_content_conflicts(http):
    _, csrf, _ = await register_user(http, f"conflict-{uuid.uuid4().hex[:8]}")

    event_id = str(uuid.uuid4())
    first = _event({"_type": "workout.started", "id": str(uuid.uuid4()), "started_at": "2026-11-11T10:00:00+08:00"}, 1)
    second = dict(first)
    second["event_id"] = event_id
    second["payload"] = {"id": str(uuid.uuid4()), "started_at": "2026-11-11T11:00:00+08:00"}
    first["event_id"] = event_id

    r1 = await http.post("/api/v1/sync/events", json={"events": [first]}, headers={"X-CSRF-Token": csrf})
    assert r1.json()["results"][0]["outcome"] == "applied"

    r2 = await http.post("/api/v1/sync/events", json={"events": [second]}, headers={"X-CSRF-Token": csrf})
    result = r2.json()["results"][0]
    assert result["outcome"] == "rejected"
    assert result["detail"]["error"] == "IDEMPOTENCY_CONFLICT"


@pytest.mark.asyncio
async def test_set_without_parent_is_dependency_pending(http):
    _, csrf, _ = await register_user(http, f"dep-{uuid.uuid4().hex[:8]}")

    session_id = str(uuid.uuid4())
    start = _event({"_type": "workout.started", "id": session_id, "started_at": "2026-11-11T10:00:00+08:00"}, 1)
    r = await http.post("/api/v1/sync/events", json={"events": [start]}, headers={"X-CSRF-Token": csrf})
    assert r.json()["results"][0]["outcome"] == "applied"

    set_event = _event(
        {
            "_type": "set.logged",
            "id": str(uuid.uuid4()),
            "session_exercise_id": str(uuid.uuid4()),  # parent never synced
            "set_index": 1,
            "reps": 10,
            "performed_at": "2026-11-11T10:05:00+08:00",
        },
        2,
    )
    r = await http.post("/api/v1/sync/events", json={"events": [set_event]}, headers={"X-CSRF-Token": csrf})
    assert r.json()["results"][0]["outcome"] == "dependency_pending"
