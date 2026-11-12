"""
API middleware (plan §6.1 / §9.2)

- Assigns a request id to every request and response header.
- Verifies Origin for state-changing API requests; login/register/reset
  additionally require a JSON content type (plan §9.2).

CSRF verification happens in the auth dependency (it needs the loaded
session); see modules/auth/dependencies.py.
"""

from urllib.parse import urlsplit
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.api.errors import ErrorCode, error_response
from app.config import get_settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# Write endpoints that run without an existing session; they still
# enforce Origin + JSON content type.
PRE_SESSION_WRITE_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/reset-password",
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request id; verify Origin (and pre-session content type) on writes."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        request.state.request_id = request.headers.get("X-Request-Id") or str(uuid4())

        if request.url.path.startswith("/api/") and request.method not in SAFE_METHODS:
            origin_error = self._check_origin(request, settings)
            if origin_error:
                return origin_error

            if request.url.path in PRE_SESSION_WRITE_PATHS:
                ctype_error = self._check_json_content_type(request)
                if ctype_error:
                    return ctype_error

        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        return response

    def _check_origin(self, request: Request, settings) -> Response | None:
        """Reject cross-site writes: Origin must be allowed or same-host."""
        origin = request.headers.get("origin")
        if origin is None:
            return None  # same-origin non-browser clients may omit Origin

        origin_host = urlsplit(origin).netloc
        request_host = request.headers.get("host", "")

        if origin in set(settings.cors_origins) or (origin_host and origin_host == request_host):
            return None

        return error_response(
            ErrorCode.ACCESS_DENIED,
            "跨站请求被拒绝",
            getattr(request.state, "request_id", None),
        )

    def _check_json_content_type(self, request: Request) -> Response | None:
        ctype = request.headers.get("content-type", "")
        if "application/json" not in ctype:
            return error_response(
                ErrorCode.VALIDATION_ERROR,
                "请求必须是 JSON 格式",
                getattr(request.state, "request_id", None),
            )
        return None
