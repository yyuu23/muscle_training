"""
Partial batch failure tests (plan §12.2): one failing event never
rolls back successful siblings in the same batch.
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
async def test_failed_middle_event_keeps_first_and_third(http, db: AsyncSession):
    _, csrf, _ = await register_user(http, f"partial-{uuid.uuid4().hex[:8]}")

    session_id = str(uuid.uuid4())
    bad_exercise_id = str(uuid.uuid4())  # parent never synced

    events = [
        # 1. valid: start workout
        _event({"_type": "workout.started", "id": session_id, "started_at": "2026-11-11T10:00:00+08:00"}, 1),
        # 2. invalid: set with missing parent
        _event(
            {
                "_type": "set.logged",
                "id": str(uuid.uuid4()),
                "session_exercise_id": bad_exercise_id,
                "set_index": 1,
                "reps": 10,
                "performed_at": "2026-11-11T10:05:00+08:00",
            },
            2,
        ),
        # 3. valid: complete the same workout
        _event({"_type": "workout.completed", "session_id": session_id, "completed_at": "2026-11-11T11:00:00+08:00"}, 3),
    ]

    response = await http.post(
        "/api/v1/sync/events",
        json={"events": events},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    results = response.json()["results"]
    outcomes = [r["outcome"] for r in results]

    assert outcomes[0] == "applied", results
    assert outcomes[1] == "dependency_pending", results
    assert outcomes[2] == "applied", results

    # First and third really committed despite the middle failure
    session = (
        await db.execute(
            select(WorkoutSession).where(WorkoutSession.id == uuid.UUID(session_id))
        )
    ).scalar_one()
    assert session.status == "completed"
