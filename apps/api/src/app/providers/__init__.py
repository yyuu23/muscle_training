"""
Providers package

get_chat_provider / get_embedding_provider / get_transcription_provider
return the configured implementation (qwen or fake).
"""

from functools import lru_cache

from app.config import get_settings
from app.providers.fake import FakeChatProvider, FakeEmbeddingProvider, FakeTranscriptionProvider


@lru_cache
def get_chat_provider():
    settings = get_settings()
    if settings.model_provider == "fake":
        return FakeChatProvider()
    from app.providers.qwen_chat import QwenChatProvider

    return QwenChatProvider()


@lru_cache
def get_embedding_provider():
    settings = get_settings()
    if settings.model_provider == "fake":
        return FakeEmbeddingProvider(dimensions=settings.embedding_dimension)
    from app.providers.qwen_embedding import QwenEmbeddingProvider

    return QwenEmbeddingProvider()


@lru_cache
def get_transcription_provider():
    settings = get_settings()
    if settings.model_provider == "fake":
        return FakeTranscriptionProvider()
    from app.providers.paraformer import ParaformerProvider

    return ParaformerProvider()


def reset_providers() -> None:
    """Test helper: drop cached providers."""
    get_chat_provider.cache_clear()
    get_embedding_provider.cache_clear()
    get_transcription_provider.cache_clear()
