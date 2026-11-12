"""
Qwen chat provider (plan §2.2 / §4.6)

DashScope OpenAI-compatible endpoint, JSON Object mode. JSON Object
mode does NOT guarantee schema conformance — the backend must validate
every output (never assume strict JSON Schema support).
"""

import json
import time

import httpx

from app.config import get_settings
from app.providers.errors import ProviderError, map_status_error
from app.providers.interfaces import ChatRequest, ChatResult, Usage

# Verified Beijing-region pricing (plan §11.4); refresh with the vendor page.
INPUT_PRICE_PER_MTOKEN_FEN = 80  # 0.8 CNY / million tokens
OUTPUT_PRICE_PER_MTOKEN_FEN = 200  # 2.0 CNY / million tokens


class QwenChatProvider:
    """Chat completions against DashScope compatible-mode."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.dashscope_api_key or ""
        self.base_url = (base_url or settings.dashscope_base_url).rstrip("/")
        self.model = model or settings.default_chat_model

    async def generate(self, request: ChatRequest) -> ChatResult:
        if not self.api_key:
            raise ProviderError("MODEL_UNAVAILABLE", "未配置 DASHSCOPE_API_KEY，模型功能不可用", retryable=False)

        payload: dict = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
        }
        if request.response_format_json:
            payload["response_format"] = {"type": "json_object"}
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise ProviderError("MODEL_TIMEOUT", "模型请求超时", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderError("MODEL_UNAVAILABLE", f"模型连接失败: {exc}", retryable=True) from exc

        if response.status_code != 200:
            raise map_status_error(response.status_code, response.text)

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("MODEL_OUTPUT_INVALID", "模型响应缺少内容", retryable=False) from exc

        usage_raw = data.get("usage") or {}
        input_tokens = int(usage_raw.get("prompt_tokens", 0))
        output_tokens = int(usage_raw.get("completion_tokens", 0))
        cost_fen = round(
            input_tokens / 1_000_000 * INPUT_PRICE_PER_MTOKEN_FEN
            + output_tokens / 1_000_000 * OUTPUT_PRICE_PER_MTOKEN_FEN
        )

        return ChatResult(
            content=content,
            usage=Usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_fen=cost_fen,
                is_estimate=True,
            ),
            raw={
                "latency_ms": int((time.monotonic() - started) * 1000),
                "model": self.model,
                "id": data.get("id"),
            },
        )


def parse_json_content(content: str) -> dict:
    """Parse model JSON output; raises ProviderError on invalid JSON."""
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ProviderError("MODEL_OUTPUT_INVALID", f"模型输出不是合法 JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ProviderError("MODEL_OUTPUT_INVALID", "模型输出必须是 JSON 对象")
    return parsed
