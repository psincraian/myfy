"""
Rate limiting middleware.

Provides global rate limiting at the ASGI layer.
"""

import logging
from typing import TYPE_CHECKING, Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .config import RateLimitSettings
from .context import (
    RateLimitContext,
    clear_rate_limit_context,
    set_rate_limit_context,
)
from .keys import RateLimitKey

if TYPE_CHECKING:
    from .store import RateLimitStore

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware for global rate limiting.

    Applies rate limits before routing, providing early rejection
    for requests that exceed global limits.

    Per-route limits are handled by the HandlerExecutor after routing.

    Usage:
        # Via RateLimitModule (recommended)
        app.add_module(RateLimitModule())

        # Manual configuration
        app.add_middleware(
            RateLimitMiddleware,
            store=InMemoryRateLimitStore(),
            settings=RateLimitSettings(),
        )
    """

    def __init__(
        self,
        app: Any,
        store: "RateLimitStore",
        settings: RateLimitSettings,
    ):
        """
        Initialize the middleware.

        Args:
            app: The ASGI application
            store: Rate limit storage backend
            settings: Rate limit configuration
        """
        super().__init__(app)
        self.store = store
        self.settings = settings

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through rate limiting."""
        # Skip if rate limiting is disabled
        if not self.settings.enabled:
            return await call_next(request)

        # Create rate limit context for this request
        rl_context = RateLimitContext()
        set_rate_limit_context(rl_context)

        try:
            # Extract client key
            client_key = self._get_client_key(request)
            rl_context._original_key = client_key

            # Check global rate limit
            if self.settings.global_requests > 0:
                global_key = f"global:{client_key}"
                result = await self.store.check_and_increment(
                    global_key,
                    self.settings.global_requests,
                    self.settings.global_window_seconds,
                )

                if not result.allowed:
                    logger.warning(
                        f"Global rate limit exceeded for {client_key}",
                        extra={"key": client_key, "limit": result.limit},
                    )
                    return self._rate_limit_response(result)

                rl_context._result = result

            # Continue to route handler
            response = await call_next(request)

            # Add rate limit headers if enabled
            if self.settings.include_headers and rl_context._result:
                for header, value in rl_context._result.headers.items():
                    response.headers[header] = value

            return response

        finally:
            clear_rate_limit_context()

    def _get_client_key(self, request: Request) -> str:
        """
        Extract client identifier from request.

        Uses the default key strategy from settings.
        Per-route key strategies are handled by the executor.
        """
        key_strategy = self.settings.default_key
        client_ip = self._get_client_ip(request)

        # Handle special key strategies
        if key_strategy == RateLimitKey.GLOBAL:
            return "global"

        if key_strategy == RateLimitKey.ENDPOINT:
            return f"endpoint:{client_ip}:{request.url.path}"

        if key_strategy == RateLimitKey.API_KEY:
            api_key = request.headers.get("X-API-Key", "")
            return f"api:{api_key}" if api_key else client_ip

        if key_strategy == RateLimitKey.SESSION:
            session_id = request.cookies.get("session_id", "")
            return f"session:{session_id}" if session_id else client_ip

        # Default: IP-based (also fallback for USER which requires auth context)
        return client_ip

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, respecting proxy headers."""
        # Check X-Forwarded-For header (set by proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header (nginx)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fallback to direct client
        if request.client:
            return request.client.host

        return "unknown"

    def _rate_limit_response(self, result) -> JSONResponse:
        """Create rate limit exceeded response."""
        return JSONResponse(
            content={
                "type": "rate_limit_exceeded",
                "title": "Rate Limit Exceeded",
                "status": 429,
                "detail": "Too many requests. Please slow down.",
                "retry_after": result.retry_after,
            },
            status_code=429,
            headers=result.headers,
        )
