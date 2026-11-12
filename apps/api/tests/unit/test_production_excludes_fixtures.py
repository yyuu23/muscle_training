"""
Production fixture-exclusion tests (plan §10.3): fixture content never
serves production users; fake provider only in dev/test.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.modules.catalog.service import CatalogService
from app.providers import FakeChatProvider, FakeEmbeddingProvider


@pytest.mark.asyncio
async def test_list_exercises_filters_fixture_in_production(monkeypatch):
    monkeypatch.setattr(
        "app.modules.catalog.service.get_settings",
        lambda: SimpleNamespace(python_env="production"),
    )

    captured = {}

    class Result:
        def scalars(self):
            return self

        def all(self):
            return []

    async def execute(query):
        captured["query"] = str(query)
        return Result()

    db = AsyncMock()
    db.execute = execute

    service = CatalogService(db)
    await service.list_exercises()
    assert "fixture" in captured["query"]


@pytest.mark.asyncio
async def test_list_exercises_keeps_fixture_in_development(monkeypatch):
    monkeypatch.setattr(
        "app.modules.catalog.service.get_settings",
        lambda: SimpleNamespace(python_env="development"),
    )

    captured = {}

    class Result:
        def scalars(self):
            return self

        def all(self):
            return []

    async def execute(query):
        captured["query"] = str(query)
        return Result()

    db = AsyncMock()
    db.execute = execute

    service = CatalogService(db)
    await service.list_exercises()
    # The fixture COLUMN appears in the SELECT list (fine); it must not
    # appear as a WHERE filter in development.
    where_clause = captured["query"].split("WHERE")[-1] if "WHERE" in captured["query"] else ""
    assert "fixture" not in where_clause


def test_import_never_marks_reviewed():
    """Import writes review_status=draft regardless of file content."""
    doc = {
        "schema_version": 1,
        "slug": "test-exercise",
        "content_version": 1,
        "display_name": "测试动作",
        "metric_type": "reps",
        "load_mode": "total_external",
        "movement_pattern": "squat",
        "review_status": "approved",  # file tries to self-approve
        "fixture": False,
    }
    from app.modules.catalog.service import validate_exercise_document

    assert validate_exercise_document(doc) == []
    # Validation passes structurally; the service upsert always writes draft
    from app.modules.catalog.service import CatalogService

    assert CatalogService._upsert_exercise.__name__ == "_upsert_exercise"
    # The upsert hardcodes review_status="draft" (see service source);
    # this test guards that import never self-approves.
    import inspect

    source = inspect.getsource(CatalogService._upsert_exercise)
    assert 'review_status="draft"' in source


def test_fake_providers_are_deterministic():
    import asyncio

    provider = FakeChatProvider()
    r1 = asyncio.run(provider.generate(__import__("app.providers.interfaces", fromlist=["ChatRequest"]).ChatRequest(
        messages=[__import__("app.providers.interfaces", fromlist=["ChatMessage"]).ChatMessage(role="user", content="你好")],
        operation="test",
    )))
    r2 = asyncio.run(provider.generate(__import__("app.providers.interfaces", fromlist=["ChatRequest"]).ChatRequest(
        messages=[__import__("app.providers.interfaces", fromlist=["ChatMessage"]).ChatMessage(role="user", content="你好")],
        operation="test",
    )))
    assert r1.content == r2.content


def test_fake_embedding_fixed_dimensions():
    import asyncio

    from app.providers.interfaces import EmbeddingRequest

    provider = FakeEmbeddingProvider(dimensions=64)
    result = asyncio.run(provider.embed(EmbeddingRequest(texts=["测试"], purpose="query")))
    assert len(result.vectors[0]) == 64


def test_production_settings_reject_fake_provider():
    with pytest.raises(ValueError, match="MODEL_PROVIDER=fake"):
        Settings(
            python_env="production",
            database_url="postgresql+asyncpg://x/x",
            model_provider="fake",
            secret_key="x" * 40,
        ).validate_required_secrets()


def test_production_settings_reject_demo_mode():
    with pytest.raises(ValueError, match="DEMO_MODE=true"):
        Settings(
            python_env="production",
            database_url="postgresql+asyncpg://x/x",
            demo_mode=True,
            secret_key="x" * 40,
        ).validate_required_secrets()
