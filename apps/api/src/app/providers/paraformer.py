"""
Paraformer transcription provider (plan §2.2 / §4.6 / §7.7)

Async submit → poll → immediately download the result to our own
storage: result URLs are short-lived and must never be stored as the
persistent address.
"""

import hashlib
import hmac
import time
from urllib.parse import quote

import httpx

from app.config import get_settings
from app.providers.errors import ProviderError, SubmissionUnknown, map_status_error
from app.providers.interfaces import ExternalTask, Transcript, TranscriptSegment

ASR_PRICE_PER_SECOND_FEN = 0.008  # 0.00008 CNY/s → fen


class ParaformerProvider:
    """File transcription via DashScope Paraformer RESTful API."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.dashscope_api_key or ""
        self.model = model or settings.default_asr_model
        self.base_url = "https://dashscope.aliyuncs.com/api/v1"

    async def submit(self, audio_url: str, *, file_name: str | None = None) -> ExternalTask:
        """Submit a transcription task; returns the external task id."""
        if not self.api_key:
            raise ProviderError("MODEL_UNAVAILABLE", "未配置 DASHSCOPE_API_KEY，转写功能不可用", retryable=False)

        payload = {
            "model": self.model,
            "input": {
                "file_urls": [audio_url],
            },
            "parameters": {
                "transcription_id": f"mt-{int(time.time())}",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/services/audio/asr/transcription",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            # Outcome unknown, no task id → needs_attention (plan §9.1)
            raise SubmissionUnknown("转写提交超时，未能确认是否已受理") from exc
        except httpx.HTTPError as exc:
            raise SubmissionUnknown(f"转写提交失败，未能确认是否已受理: {exc}") from exc

        if response.status_code >= 500:
            raise SubmissionUnknown(f"上游错误，未取得任务号: {response.status_code}")
        if response.status_code != 200:
            raise map_status_error(response.status_code, response.text)

        data = response.json()
        output = data.get("output") or {}
        task_id = output.get("task_id")
        if not task_id:
            raise SubmissionUnknown("提交成功但未返回任务号")

        return ExternalTask(task_id=task_id, status="submitted")

    async def poll(self, task_id: str) -> ExternalTask:
        """Poll task status."""
        if not self.api_key:
            raise ProviderError("MODEL_UNAVAILABLE", "未配置 DASHSCOPE_API_KEY", retryable=False)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/tasks/{quote(task_id)}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
        except httpx.TimeoutException as exc:
            raise ProviderError("MODEL_TIMEOUT", "转写状态查询超时", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderError("MODEL_UNAVAILABLE", f"转写状态查询失败: {exc}", retryable=True) from exc

        if response.status_code == 404:
            return ExternalTask(task_id=task_id, status="unknown")
        if response.status_code != 200:
            raise map_status_error(response.status_code, response.text)

        data = response.json()
        output = data.get("output") or {}
        status = output.get("task_status")

        status_map = {
            "PENDING": "running",
            "RUNNING": "running",
            "SUCCEEDED": "succeeded",
            "FAILED": "failed",
        }
        internal_status = status_map.get(status, "unknown")

        result_url: str | None = None
        if internal_status == "succeeded":
            results = output.get("results") or []
            if results:
                transcription_url = (results[0] or {}).get("transcription_url")
                result_url = transcription_url

        return ExternalTask(task_id=task_id, status=internal_status, result_url=result_url)

    async def fetch_result(self, result_url: str) -> Transcript:
        """Download the transcript JSON immediately (short-lived URL)."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(result_url)
        except httpx.TimeoutException as exc:
            raise ProviderError("MODEL_TIMEOUT", "转写结果下载超时", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderError("MODEL_UNAVAILABLE", f"转写结果下载失败: {exc}", retryable=True) from exc

        if response.status_code != 200:
            raise map_status_error(response.status_code, "下载转写结果失败")

        data = response.json()
        segments: list[TranscriptSegment] = []

        transcripts = data.get("transcripts") or []
        for transcript in transcripts:
            for sentence in transcript.get("sentences") or []:
                begin = sentence.get("begin_time")
                end = sentence.get("end_time")
                text = sentence.get("text", "").strip()
                if text and begin is not None and end is not None:
                    segments.append(
                        TranscriptSegment(
                            start_ms=int(begin),
                            end_ms=int(end),
                            text=text,
                        )
                    )

        if not segments:
            # Whole-text fallback keeps the raw transcript durable
            full_text = (transcripts[0] or {}).get("text") if transcripts else None
            if full_text:
                segments = [TranscriptSegment(start_ms=0, end_ms=0, text=full_text)]

        return Transcript(segments=segments, raw=data)


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Constant-time webhook signature check when callbacks are enabled."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
