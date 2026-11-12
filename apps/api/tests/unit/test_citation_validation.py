"""
Citation validation tests (plan §7.9 / §6.5): citations must belong to
the retrieval set, come from accessible sources, and reference the
active revision.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.rag.citations import extract_citations, validate_citations


def _chunk(revision_id):
    return SimpleNamespace(id=uuid.uuid4(), source_revision_id=revision_id)


def _revision(source_id):
    return SimpleNamespace(id=uuid.uuid4(), source_id=source_id)


def _source(source_id, *, visibility="private", owner="user-1", status="ready", active_revision=None):
    return SimpleNamespace(
        id=source_id, visibility=visibility, owner_user_id=owner, status=status,
        active_revision_id=active_revision,
    )


class _DB:
    """AsyncMock get() returning objects by (model, id) key."""

    def __init__(self, by_id):
        self._by_id = by_id

    async def get(self, model, obj_id):
        return self._by_id.get((model.__name__, obj_id))

    async def execute(self, query):
        result = SimpleNamespace(scalar_one_or_none=lambda: self._source_result)
        return result


@pytest.mark.asyncio
async def test_citation_outside_retrieval_rejected():
    retrieved = [uuid.uuid4()]
    cited = str(uuid.uuid4())  # not in retrieval
    checks = await validate_citations(AsyncMock(), uuid.uuid4(), retrieved, [cited])
    assert checks[0].valid is False
    assert "不在本次检索结果" in checks[0].reason  # fabrication guard


@pytest.mark.asyncio
async def test_non_uuid_citation_rejected():
    checks = await validate_citations(AsyncMock(), uuid.uuid4(), [uuid.uuid4()], ["not-a-uuid"])
    assert checks[0].valid is False
    assert "UUID" in checks[0].reason


@pytest.mark.asyncio
async def test_valid_shared_source_citation():
    chunk = _chunk(revision_id := uuid.uuid4())
    source = _source(uuid.uuid4(), visibility="shared", active_revision=revision_id)
    db = _DB({
        ("KnowledgeChunk", chunk.id): chunk,
        ("SourceRevision", revision_id): _revision(source.id),
    })
    db._source_result = source
    user = uuid.UUID(int=999)  # different user, shared source OK
    checks = await validate_citations(db, user, [chunk.id], [str(chunk.id)])
    assert checks[0].valid is True


@pytest.mark.asyncio
async def test_private_source_other_user_rejected():
    chunk = _chunk(revision_id := uuid.uuid4())
    source = _source(uuid.uuid4(), visibility="private", owner="owner-1", active_revision=revision_id)
    db = _DB({
        ("KnowledgeChunk", chunk.id): chunk,
        ("SourceRevision", revision_id): _revision(source.id),
    })
    db._source_result = source
    checks = await validate_citations(db, uuid.UUID(int=999), [chunk.id], [str(chunk.id)])
    assert checks[0].valid is False
    assert "无权" in checks[0].reason


@pytest.mark.asyncio
async def test_withdrawn_source_rejected():
    chunk = _chunk(revision_id := uuid.uuid4())
    source = _source(uuid.uuid4(), status="withdrawn", active_revision=revision_id)
    db = _DB({
        ("KnowledgeChunk", chunk.id): chunk,
        ("SourceRevision", revision_id): _revision(source.id),
    })
    db._source_result = source
    checks = await validate_citations(db, uuid.UUID(int=999), [chunk.id], [str(chunk.id)])
    assert checks[0].valid is False
    assert "撤回" in checks[0].reason


@pytest.mark.asyncio
async def test_stale_revision_rejected():
    """Citing a superseded revision of the same source is invalid."""
    chunk = _chunk(revision_id := uuid.uuid4())
    newer_revision = uuid.uuid4()
    source = _source(uuid.uuid4(), visibility="shared", active_revision=newer_revision)
    db = _DB({
        ("KnowledgeChunk", chunk.id): chunk,
        ("SourceRevision", revision_id): _revision(source.id),
    })
    db._source_result = source
    checks = await validate_citations(db, uuid.UUID(int=999), [chunk.id], [str(chunk.id)])
    assert checks[0].valid is False
    assert "有效版本" in checks[0].reason


def test_extract_citations_various_shapes():
    answer = {"citations": ["plain-id", {"chunk_id": "dict-id", "quote": "原文"}, None, ""]}
    assert extract_citations(answer) == ["plain-id", "dict-id"]


def test_extract_citations_empty():
    assert extract_citations({}) == []
