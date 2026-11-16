"""
User deletion (plan §9.5 / §12.2): delete_user_data wipes business
rows across tables and records the deletion ledger for restore
re-application.
"""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.db.models.auth import AuthSession, User
from app.db.models.nutrition import Measurement
from app.db.models.operations import DeletionLedger
from app.db.models.profile import Profile, UserState
from app.db.models.training import WorkoutSession
from app.modules.deletion.ledger import delete_user_data
from app.utils.password import hash_password

pytestmark = pytest.mark.integration

FUTURE = datetime.now(tz=None) + timedelta(days=1)


async def _make_user(db, username: str) -> User:
    user = User(
        id=uuid.uuid4(),
        username_normalized=username,
        display_name=username,
        password_hash=hash_password("delete-me-password-123"),
        role="member",
        status="active",
    )
    db.add(user)
    await db.flush()
    return user


async def test_delete_user_data_wipes_and_ledgers(db):
    user = await _make_user(db, f"gone-{uuid.uuid4().hex[:8]}")
    keeper = await _make_user(db, f"keep-{uuid.uuid4().hex[:8]}")

    db.add(Profile(user_id=user.id, version=1))
    db.add(Profile(user_id=keeper.id, version=1))
    db.add(UserState(user_id=user.id, planning_revision=1))
    db.add(AuthSession(user_id=user.id, token_hash="t" * 64, csrf_token="c" * 32, expires_at=FUTURE))
    db.add(WorkoutSession(user_id=user.id, started_at=FUTURE, status="completed", completed_at=FUTURE, version=1))
    db.add(
        Measurement(
            user_id=keeper.id,
            measurement_type="weight",
            value=72.5,
            unit="kg",
            observed_at=FUTURE,
            version=1,
        )
    )
    await db.commit()

    stats = await delete_user_data(db, user.id)

    # Deleted user's data is gone everywhere…
    assert (await db.execute(select(func.count()).select_from(Profile).where(Profile.user_id == user.id))).scalar() == 0
    assert (await db.execute(select(func.count()).select_from(UserState).where(UserState.user_id == user.id))).scalar() == 0
    assert (await db.execute(select(func.count()).select_from(WorkoutSession).where(WorkoutSession.user_id == user.id))).scalar() == 0
    assert (await db.execute(select(func.count()).select_from(AuthSession).where(AuthSession.user_id == user.id))).scalar() == 0

    # …the ledger recorded the wipe…
    ledger = (await db.execute(select(DeletionLedger).where(DeletionLedger.user_id == user.id))).scalars().all()
    assert len(ledger) == 1
    assert stats and any((isinstance(v, int) and v > 0) for v in stats.values())

    # …and other users are untouched.
    assert (await db.execute(select(func.count()).select_from(Profile).where(Profile.user_id == keeper.id))).scalar() == 1
    assert (await db.execute(select(func.count()).select_from(Measurement).where(Measurement.user_id == keeper.id))).scalar() == 1
