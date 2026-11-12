"""
Deterministic fake providers (plan §4.6 / §10.3)

Development/testing ONLY — production must never run with
MODEL_PROVIDER=fake. Deterministic responses plus fault injection;
fake results are never evidence of real model quality.
"""

import hashlib
import json
import math
from dataclasses import dataclass, field

from app.providers.errors import ProviderError
from app.providers.interfaces import (
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
    ExternalTask,
    Transcript,
    TranscriptSegment,
    Usage,
)


@dataclass
class FaultInjection:
    """Scripted failures for testing failure paths."""

    chat_error: str | None = None
    chat_invalid_json: bool = False
    embedding_error: str | None = None
    embedding_bad_dimensions: bool = False
    transcription_submit_unknown: bool = False


@dataclass
class FakeChatProvider:
    """Deterministic chat: routes by operation with scripted outputs."""

    scripted: dict[str, str] = field(default_factory=dict)
    faults: FaultInjection = field(default_factory=FaultInjection)
    calls: list[ChatRequest] = field(default_factory=list)

    async def generate(self, request: ChatRequest) -> ChatResult:
        self.calls.append(request)

        if self.faults.chat_error:
            raise ProviderError(self.faults.chat_error, "注入的模型故障", retryable=True)
        if self.faults.chat_invalid_json:
            return ChatResult(content="这不是 JSON", usage=Usage(input_tokens=1, output_tokens=1))

        content = self.scripted.get(request.operation)
        if content is None:
            content = json.dumps(
                {"status": "answered", "answer_markdown": "确定性测试回答", "citations": [], "missing_fields": []},
                ensure_ascii=False,
            )
        return ChatResult(
            content=content,
            usage=Usage(
                input_tokens=sum(len(m.content) // 4 + 1 for m in request.messages),
                output_tokens=len(content) // 4 + 1,
                estimated_cost_fen=1,
                is_estimate=True,
            ),
        )


@dataclass
class FakeEmbeddingProvider:
    """Deterministic hash-based embeddings with fixed dimensions."""

    dimensions: int = 1024
    faults: FaultInjection = field(default_factory=FaultInjection)

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "big")
        return [
            round(math.sin(seed + i) * 0.5 + 0.5, 6)
            for i in range(self.dimensions)
        ]

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        if self.faults.embedding_error:
            raise ProviderError(self.faults.embedding_error, "注入的向量故障", retryable=True)

        dimensions = 8 if self.faults.embedding_bad_dimensions else self.dimensions
        digest = hashlib.sha256(b"".join(t.encode() for t in request.texts)).digest()
        seed = int.from_bytes(digest[:8], "big")

        def vector(text: str) -> list[float]:
            base = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")
            return [round(math.sin(base * (i + 1) + seed) * 0.5 + 0.5, 6) for i in range(dimensions)]

        return EmbeddingResult(
            vectors=[vector(t) for t in request.texts],
            model="fake-embedding",
            dimensions=dimensions,
            usage=Usage(input_tokens=sum(len(t) for t in request.texts), is_estimate=True),
        )


@dataclass
class FakeTranscriptionProvider:
    """Deterministic transcription with resumable external tasks."""

    faults: FaultInjection = field(default_factory=FaultInjection)
    tasks: dict[str, dict] = field(default_factory=dict)
    _counter: int = 0

    async def submit(self, audio_url: str, *, file_name: str | None = None) -> ExternalTask:
        if self.faults.transcription_submit_unknown:
            raise ProviderError("SUBMISSION_UNKNOWN", "注入的提交结果未知", retryable=False)

        self._counter += 1
        task_id = f"fake-task-{self._counter}"
        self.tasks[task_id] = {
            "status": "succeeded",
            "url": audio_url,
            "polled": 0,
        }
        return ExternalTask(task_id=task_id, status="submitted")

    async def poll(self, task_id: str) -> ExternalTask:
        task = self.tasks.get(task_id)
        if task is None:
            return ExternalTask(task_id=task_id, status="unknown")
        task["polled"] += 1
        if task_id.endswith("-hang"):
            return ExternalTask(task_id=task_id, status="running")
        return ExternalTask(
            task_id=task_id,
            status=task["status"],
            result_url=f"fake://results/{task_id}",
        )

    async def fetch_result(self, result_url: str) -> Transcript:
        task_id = result_url.rsplit("/", 1)[-1]
        url = self.tasks.get(task_id, {}).get("url", "")
        digest = hashlib.sha256(url.encode()).hexdigest()[:6]
        return Transcript(
            segments=[
                TranscriptSegment(start_ms=0, end_ms=5000, text=f"确定性转写第一段 {digest}"),
                TranscriptSegment(start_ms=5000, end_ms=12000, text="确定性转写第二段，包含否定：不要锁死膝盖。"),
            ],
            raw={"task_id": task_id},
        )
