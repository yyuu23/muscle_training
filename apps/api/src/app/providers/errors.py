"""
Provider error mapping (plan §4.6)

Vendor errors become stable internal errors; callers never see raw
upstream payloads.
"""


class ProviderError(Exception):
    """Stable internal provider error."""

    def __init__(self, code: str, message: str, retryable: bool = False):
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


class ProviderUnavailable(ProviderError):
    def __init__(self, message: str = "模型服务不可用"):
        super().__init__("MODEL_UNAVAILABLE", message, retryable=True)


class ProviderTimeout(ProviderError):
    def __init__(self, message: str = "模型服务超时"):
        super().__init__("MODEL_TIMEOUT", message, retryable=True)


class ProviderRateLimited(ProviderError):
    def __init__(self, message: str = "模型服务限流"):
        super().__init__("RATE_LIMITED", message, retryable=True)


class ProviderAuthError(ProviderError):
    def __init__(self, message: str = "模型服务认证失败"):
        super().__init__("PROVIDER_AUTH", message, retryable=False)


class ProviderBadRequest(ProviderError):
    def __init__(self, message: str = "模型服务请求被拒绝"):
        super().__init__("PROVIDER_BAD_REQUEST", message, retryable=False)


class SubmissionUnknown(ProviderError):
    """Submit outcome unknown and no task id obtained (plan §9.1):
    must surface as needs_attention, never a blind resubmit."""

    def __init__(self, message: str = "提交结果未知，未取得任务号"):
        super().__init__("SUBMISSION_UNKNOWN", message, retryable=False)


def map_status_error(status_code: int, body: str) -> ProviderError:
    """Map an HTTP status to a stable provider error."""
    snippet = body[:200]
    if status_code == 401 or status_code == 403:
        return ProviderAuthError(f"认证失败: {snippet}")
    if status_code == 429:
        return ProviderRateLimited(f"限流: {snippet}")
    if status_code >= 500:
        return ProviderUnavailable(f"上游错误 {status_code}: {snippet}")
    return ProviderBadRequest(f"请求被拒绝 {status_code}: {snippet}")
