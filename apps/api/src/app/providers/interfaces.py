"""
Provider interfaces (plan §4.6)

Providers never modify business tables and never forward health data
to another unconfigured vendor.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ChatRequest:
    messages: list[ChatMessage]
    operation: str = "chat"
    response_format_json: bool = True
    max_tokens: int | None = None
    temperature: float = 0.3


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_fen: int = 0  # 0.01 CNY units
    is_estimate: bool = True


@dataclass
class ChatResult:
    content: str
    usage: Usage = field(default_factory=Usage)
    raw: dict[str, Any] | None = None


@dataclass
class EmbeddingRequest:
    texts: list[str]
    purpose: str = "indexing"  # or "query"


@dataclass
class EmbeddingResult:
    vectors: list[list[float]]
    model: str
    dimensions: int
    usage: Usage = field(default_factory=Usage)


@dataclass
class ExternalTask:
    task_id: str
    status: str  # "submitted" | "running" | "succeeded" | "failed" | "unknown"
    result_url: str | None = None


@dataclass
class TranscriptSegment:
    start_ms: int
    end_ms: int
    text: str


@dataclass
class Transcript:
    segments: list[TranscriptSegment]
    raw: dict[str, Any] | None = None


class ChatProvider(Protocol):
    async def generate(self, request: ChatRequest) -> ChatResult: ...


class EmbeddingProvider(Protocol):
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...


class TranscriptionProvider(Protocol):
    async def submit(self, audio_url: str, *, file_name: str | None = None) -> ExternalTask: ...

    async def poll(self, task_id: str) -> ExternalTask: ...

    async def fetch_result(self, result_url: str) -> Transcript: ...
