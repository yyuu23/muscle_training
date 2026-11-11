"""
Sync middleware for idempotency support
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.session import async_session_maker
from app.modules.sync.service import SyncService


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle idempotent requests

    Checks X-Idempotency-Key header and returns cached response if available
    """

    async def dispatch(self, request: Request, call_next):
        """Process request with idempotency check"""
        idempotency_key = request.headers.get("X-Idempotency-Key")

        # Only apply to POST/PUT/PATCH methods
        if request.method not in ["POST", "PUT", "PATCH"] or not idempotency_key:
            return await call_next(request)

        # Get user from auth (simplified - would need actual auth check)
        user_id = request.state.user_id if hasattr(request.state, "user_id") else None

        if not user_id:
            return await call_next(request)

        # Check for existing response
        async with async_session_maker() as db:
            service = SyncService(db)
            cached_response = await service.check_idempotency(user_id, idempotency_key)

            if cached_response:
                # Return cached response
                return Response(
                    content=cached_response.get("body", ""),
                    status_code=cached_response.get("status_code", 200),
                    headers={"X-Idempotency-Replay": "true"},
                )

        # Process request normally
        return await call_next(request)
