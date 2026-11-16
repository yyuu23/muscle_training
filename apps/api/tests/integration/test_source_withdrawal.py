"""
Source withdrawal (plan §7.10 / §12.2): a withdrawn source is
excluded from retrieval immediately, stays queryable for history, and
only the owner or an admin may withdraw.
"""

import uuid

import pytest

from app.api.errors import ApiError
from app.db.models.auth import User
from app.db.models.knowledge import KnowledgeSource
from app.modules.knowledge.service import KnowledgeService
from app.utils.password import hash_password

pytestmark = pytest.mark.integration


async def _make_user(db, username: str, role: str = "member") -> User:
    user = User(
        id=uuid.uuid4(),
        username_normalized=username,
        display_name=username,
        password_hash=hash_password("withdraw-password-123"),
        role=role,
        status="active",
    )
    db.add(user)
    await db.flush()
    return user


def _source(owner) -> KnowledgeSource:
    return KnowledgeSource(
        id=uuid.uuid4(),
        owner_user_id=owner.id,
        visibility="shared",
        title=f"共享-{uuid.uuid4().hex[:6]}",
        source_type="document",
        status="ready",
    )


async def test_withdraw_excludes_from_new_retrievals(db):
    alice = await _make_user(db, f"a-{uuid.uuid4().hex[:8]}")
    bob = await _make_user(db, f"b-{uuid.uuid4().hex[:8]}")

    source = _source(alice)
    db.add(source)
    await db.commit()

    service = KnowledgeService(db)
    bob_rows, _ = await service.list_sources(bob.id)
    assert source.id in {r.id for r in bob_rows}

    withdrawn = await service.withdraw_source(source.id, alice.id, is_admin=False)
    assert withdrawn.status == "withdrawn"

    # Withdrawn sources disappear from listings for everyone (owner
    # keeps history access via direct detail, not via the shared list).
    bob_rows, _ = await service.list_sources(bob.id)
    assert source.id not in {r.id for r in bob_rows}
    # History intact: the row itself is not deleted.
    detail = await service.source_detail(source.id)
    assert detail["source"].status == "withdrawn"


async def test_non_owner_cannot_withdraw(db):
    alice = await _make_user(db, f"a-{uuid.uuid4().hex[:8]}")
    mallory = await _make_user(db, f"m-{uuid.uuid4().hex[:8]}")
    admin = await _make_user(db, f"adm-{uuid.uuid4().hex[:8]}", role="admin")

    source = _source(alice)
    db.add(source)
    await db.commit()

    service = KnowledgeService(db)
    with pytest.raises(ApiError):
        await service.withdraw_source(source.id, mallory.id, is_admin=False)

    # Admin may withdraw on behalf (content moderation).
    withdrawn = await service.withdraw_source(source.id, admin.id, is_admin=True)
    assert withdrawn.status == "withdrawn"
