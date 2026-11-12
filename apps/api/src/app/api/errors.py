"""
Unified API error specification (plan §6.1)

Error envelope:
{
  "error": {
    "code": "PLAN_CONTEXT_STALE",
    "message": "...",
    "request_id": "uuid",
    "details": {}
  }
}
"""

from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)


class ErrorCode:
    """Fixed error codes (plan §6.1)."""

    AUTH_REQUIRED = "AUTH_REQUIRED"
    ACCESS_DENIED = "ACCESS_DENIED"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    PLAN_CONTEXT_STALE = "PLAN_CONTEXT_STALE"
    CONTENT_NOT_READY = "CONTENT_NOT_READY"
    INSUFFICIENT_PROFILE = "INSUFFICIENT_PROFILE"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    MODEL_OUTPUT_INVALID = "MODEL_OUTPUT_INVALID"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    RATE_LIMITED = "RATE_LIMITED"
    DEPENDENCY_PENDING = "DEPENDENCY_PENDING"


STATUS_BY_CODE = {
    ErrorCode.AUTH_REQUIRED: HTTP_401_UNAUTHORIZED,
    ErrorCode.ACCESS_DENIED: HTTP_403_FORBIDDEN,
    ErrorCode.NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.VALIDATION_ERROR: HTTP_400_BAD_REQUEST,
    ErrorCode.VERSION_CONFLICT: HTTP_409_CONFLICT,
    ErrorCode.IDEMPOTENCY_CONFLICT: HTTP_409_CONFLICT,
    ErrorCode.PLAN_CONTEXT_STALE: HTTP_409_CONFLICT,
    ErrorCode.CONTENT_NOT_READY: HTTP_409_CONFLICT,
    ErrorCode.INSUFFICIENT_PROFILE: HTTP_422_UNPROCESSABLE_CONTENT,
    ErrorCode.MODEL_UNAVAILABLE: HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.MODEL_OUTPUT_INVALID: HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.BUDGET_EXHAUSTED: HTTP_429_TOO_MANY_REQUESTS,
    ErrorCode.RATE_LIMITED: HTTP_429_TOO_MANY_REQUESTS,
    ErrorCode.DEPENDENCY_PENDING: HTTP_409_CONFLICT,
}


class ApiError(Exception):
    """Domain error carrying a fixed error code."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = STATUS_BY_CODE.get(code, HTTP_400_BAD_REQUEST)
        super().__init__(message)


def error_response(
    code: str,
    message: str,
    request_id: str | None = None,
    details: dict | None = None,
    status_code: int | None = None,
) -> JSONResponse:
    """Build the unified error envelope."""
    return JSONResponse(
        status_code=status_code or STATUS_BY_CODE.get(code, HTTP_400_BAD_REQUEST),
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id or str(uuid4()),
                "details": details or {},
            }
        },
    )


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    """Handle ApiError raised in routes/services."""
    request_id = getattr(request.state, "request_id", None)
    return error_response(exc.code, exc.message, request_id, exc.details, exc.status_code)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Convert FastAPI validation errors to the unified envelope."""
    request_id = getattr(request.state, "request_id", None)
    details = {}
    for err in exc.errors():
        loc = ".".join(str(part) for part in err.get("loc", ()) if part != "body")
        details[loc or "body"] = err.get("msg", "invalid")
    return error_response(
        ErrorCode.VALIDATION_ERROR,
        "请求参数不合法",
        request_id,
        details,
        HTTP_400_BAD_REQUEST,
    )


async def http_error_handler(request: Request, exc) -> JSONResponse:
    """Convert plain HTTPException (e.g. 404 routing) to the envelope."""
    from fastapi import HTTPException  # local import to avoid cycle

    if isinstance(exc, HTTPException):
        code = {
            401: ErrorCode.AUTH_REQUIRED,
            403: ErrorCode.ACCESS_DENIED,
            404: ErrorCode.NOT_FOUND,
            429: ErrorCode.RATE_LIMITED,
        }.get(exc.status_code, ErrorCode.VALIDATION_ERROR if exc.status_code < 500 else "INTERNAL_ERROR")
        request_id = getattr(request.state, "request_id", None)
        detail = exc.detail if isinstance(exc.detail, str) else "请求失败"
        return error_response(code, detail, request_id, {}, exc.status_code)
    request_id = getattr(request.state, "request_id", None)
    return error_response("INTERNAL_ERROR", "服务器内部错误", request_id, {}, HTTP_500_INTERNAL_SERVER_ERROR)
