"""
Rate limit decorator for routes.

Attaches rate limit configuration to handler functions.
"""

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from .keys import RateLimitKey
from .types import RateLimitConfig

P = ParamSpec("P")
R = TypeVar("R")

# Attribute name for storing rate limit config on handlers
RATE_LIMIT_ATTR = "_rate_limit_config"


def rate_limit(
    requests: int,
    window_seconds: int = 60,
    *,
    key: RateLimitKey | str = RateLimitKey.IP,
    scope: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to apply rate limiting to a route.

    Attach rate limit configuration to a handler function.
    The actual rate limiting is performed by the middleware
    or handler executor at runtime.

    Args:
        requests: Maximum requests allowed in the window
        window_seconds: Time window in seconds (default: 60)
        key: Key strategy for identifying clients (default: IP)
        scope: Optional scope name to group routes under same bucket

    Returns:
        Decorated function with rate limit metadata

    Examples:
        # Basic rate limiting (100 requests per minute per IP)
        @route.get("/api/data")
        @rate_limit(100)
        async def get_data() -> dict:
            ...

        # Stricter limit with longer window
        @route.post("/api/login")
        @rate_limit(5, window_seconds=300)  # 5 per 5 minutes
        async def login(credentials: LoginRequest) -> Token:
            ...

        # Rate limit by authenticated user
        @route.get("/api/profile")
        @rate_limit(50, key=RateLimitKey.USER)
        async def get_profile(user: User) -> Profile:
            ...

        # Rate limit by API key
        @route.get("/api/partner/data")
        @rate_limit(1000, key=RateLimitKey.API_KEY)
        async def partner_api() -> dict:
            ...

        # Shared limit across multiple routes
        @route.post("/api/expensive-a")
        @rate_limit(10, scope="expensive")
        async def expensive_a() -> dict:
            ...

        @route.post("/api/expensive-b")
        @rate_limit(10, scope="expensive")  # Shares bucket with expensive_a
        async def expensive_b() -> dict:
            ...

        # Static key for global limit
        @route.post("/api/webhook")
        @rate_limit(100, key="webhooks")  # All webhook calls share one bucket
        async def webhook(payload: WebhookPayload) -> None:
            ...
    """
    config = RateLimitConfig(
        requests=requests,
        window_seconds=window_seconds,
        key=key,
        scope=scope,
    )

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        # Attach config as metadata (analyzed at startup)
        setattr(func, RATE_LIMIT_ATTR, config)

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return func(*args, **kwargs)

        # Also set on wrapper to handle decorator ordering
        setattr(wrapper, RATE_LIMIT_ATTR, config)
        return wrapper  # type: ignore[return-value]

    return decorator


def get_rate_limit_config(handler: Callable) -> RateLimitConfig | None:
    """
    Get rate limit configuration from a handler function.

    Args:
        handler: The route handler function

    Returns:
        RateLimitConfig if decorated, None otherwise
    """
    return getattr(handler, RATE_LIMIT_ATTR, None)
