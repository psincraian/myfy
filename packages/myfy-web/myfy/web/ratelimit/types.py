"""
Shared types for rate limiting.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .keys import RateLimitKey

if TYPE_CHECKING:
    from myfy.web.context import RequestContext


@dataclass(frozen=True)
class RateLimitConfig:
    """
    Configuration for a rate-limited route.

    Attached to handler functions by the @rate_limit decorator.
    Analyzed at startup during route compilation.

    Attributes:
        requests: Maximum requests allowed in the window
        window_seconds: Time window in seconds (default: 60)
        key: Key strategy for identifying clients
        scope: Optional scope name to group routes under same limit bucket
    """

    requests: int
    window_seconds: int = 60
    key: RateLimitKey | str = RateLimitKey.IP
    scope: str | None = None

    def __post_init__(self) -> None:
        if self.requests <= 0:
            raise ValueError("requests must be positive")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


@dataclass
class RateLimitResult:
    """
    Result of a rate limit check.

    Attributes:
        allowed: Whether the request is allowed
        remaining: Number of requests remaining in the window
        reset_at: Unix timestamp when the window resets
        retry_after: Seconds until the client can retry (if not allowed)
        limit: The maximum requests allowed in the window
    """

    allowed: bool
    remaining: int
    reset_at: float
    retry_after: int = 0
    limit: int = 0

    @property
    def headers(self) -> dict[str, str]:
        """Generate standard rate limit headers."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
            "X-RateLimit-Reset": str(int(self.reset_at)),
        }
        if not self.allowed:
            headers["Retry-After"] = str(self.retry_after)
        return headers


# Type alias for custom key extraction functions
KeyExtractor = Callable[["RequestContext"], str]
