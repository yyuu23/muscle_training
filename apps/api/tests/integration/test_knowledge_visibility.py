"""
Knowledge visibility (plan §5.7 / §12.2): private sources are invisible
to other users; the shared library is visible to everyone; admin share
publishes, owner/admin withdraw excludes from listing.
"""

import uuid
from uuid import UUID

import pytest

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
        password_hash=hash_password("knowledge-password-123"),
        role=role,
        status="active",
    )
    db.add(user)
    await db.flush()
    return user


def _source(owner: UUID | None, *, visibility: str = "private", status: str = "ready") -> KnowledgeSource:
    return KnowledgeSource(
        id=uuid.uuid4(),
        owner_user_id=owner,
        visibility=visibility,
        title=f"来源-{uuid.uuid4().hex[:6]}",
        source_type="document",
        status=status,
    )


async def test_private_sources_are_user_scoped(db):
    alice = await _make_user(db, f"a-{uuid.uuid4().hex[:8]}")
    bob = await _make_user(db, f"b-{uuid.uuid4().hex[:8]}")

    db.add(_source(alice.id))
    db.add(_source(bob.id))
    await db.commit()

    service = KnowledgeService(db)
    alice_rows, _ = await service.list_sources(alice.id)
    bob_rows, _ = await service.list_sources(bob.id)

    assert {r.owner_user_id for r in alice_rows} == {alice.id}
    assert {r.owner_user_id for r in bob_rows} == {bob.id}


async def test_shared_library_visible_to_all(db):
    alice = await _make_user(db, f"a-{uuid.uuid4().hex[:8]}")
    bob = await _make_user(db, f"b-{uuid.uuid4().hex[:8]}")

    db.add(_source(alice.id, visibility="shared"))
    db.add(_source(alice.id))  # still private
    await db.commit()

    service = KnowledgeService(db)
    bob_rows, _ = await service.list_sources(bob.id)
    assert len(bob_rows) == 1
    assert bob_rows[0].visibility == "shared"


async def test_share_requires_ready_then_publishes(db):
    alice = await _make_user(db, f"a-{uuid.uuid4().hex[:8]}")
    admin = await _make_user(db, f"adm-{uuid.uuid4().hex[:8]}", role="admin")
    bob = await _make_user(db, f"b-{uuid.uuid4().hex[:8]}")

    processing = _source(alice.id, status="processing")
    ready = _source(alice.id, status="ready")
    db.add_all([processing, ready])
    await db.commit()

    service = KnowledgeService(db)

    from app.api.errors import ApiError

    with pytest.raises(ApiError):
        await service.share_source(processing.id, admin.id)

    await service.share_source(ready.id, admin.id)
    assert ready.visibility == "shared"

    bob_rows, _ = await service.list_sources(bob.id)
    assert ready.id in {r.id for r in bob_rows}
