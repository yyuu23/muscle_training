"""
Qwen embedding provider (plan §2.2 / §4.6)

Batch embedding with dimension verification: query and document
vectors must use the same model and dimensions (plan §7.9).
"""

import httpx

from app.config import get_settings
from app.providers.errors import ProviderError, map_status_error
from app.providers.interfaces import EmbeddingRequest, EmbeddingResult, Usage

EMBEDDING_PRICE_PER_MTOKEN_FEN = 50  # 0.5 CNY / million tokens


class QwenEmbeddingProvider:
    """Text embeddings via DashScope compatible-mode."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.dashscope_api_key or ""
        self.base_url = (base_url or settings.dashscope_base_url).rstrip("/")
        self.model = model or settings.default_embedding_model
        self.expected_dimensions = settings.embedding_dimension

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        if not self.api_key:
            raise ProviderError("MODEL_UNAVAILABLE", "未配置 DASHSCOPE_API_KEY，向量功能不可用", retryable=False)

        # Batch with a conservative ceiling
        texts = request.texts[:25]

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "input": texts,
                        "dimensions": self.expected_dimensions,
                        "text_type": "document" if request.purpose == "indexing" else "query",
                    },
                )
        except httpx.TimeoutException as exc:
            raise ProviderError("MODEL_TIMEOUT", "向量请求超时", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderError("MODEL_UNAVAILABLE", f"向量连接失败: {exc}", retryable=True) from exc

        if response.status_code != 200:
            raise map_status_error(response.status_code, response.text)

        data = response.json()
        embedding_rows = data.get("data") or []
        vectors = [row["embedding"] for row in sorted(embedding_rows, key=lambda r: r.get("index", 0))]

        if len(vectors) != len(texts):
            raise ProviderError("MODEL_OUTPUT_INVALID", "向量数量与输入不一致", retryable=False)

        for vector in vectors:
            if len(vector) != self.expected_dimensions:
                raise ProviderError(
                    "MODEL_OUTPUT_INVALID",
                    f"向量维度 {len(vector)} 与配置 {self.expected_dimensions} 不一致",
                    retryable=False,
                )

        usage_raw = data.get("usage") or {}
        total_tokens = int(usage_raw.get("total_tokens", sum(len(t) for t in texts)))

        return EmbeddingResult(
            vectors=vectors,
            model=self.model,
            dimensions=self.expected_dimensions,
            usage=Usage(
                input_tokens=total_tokens,
                estimated_cost_fen=round(total_tokens / 1_000_000 * EMBEDDING_PRICE_PER_MTOKEN_FEN),
                is_estimate=True,
            ),
        )
