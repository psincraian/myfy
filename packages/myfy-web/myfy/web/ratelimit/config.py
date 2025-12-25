"""
Rate limiting configuration.
"""

from pydantic import Field

from myfy.core.config import BaseSettings

from .keys import RateLimitKey


class RateLimitSettings(BaseSettings):
    """
    Rate limit settings.

    Configure global rate limiting behavior.
    Per-route limits can override these defaults via the @rate_limit decorator.
    """

    # Global enable/disable
    enabled: bool = Field(
        default=True,
        description="Enable rate limiting (set to False to disable globally)",
    )

    # Default limits for routes without explicit @rate_limit decorator
    default_requests: int = Field(
        default=100,
        description="Default requests per window for undecorated routes",
    )
    default_window_seconds: int = Field(
        default=60,
        description="Default time window in seconds",
    )
    default_key: RateLimitKey = Field(
        default=RateLimitKey.IP,
        description="Default key strategy",
    )

    # Global limits (applied before route-specific limits)
    global_requests: int = Field(
        default=1000,
        description="Global requests per window per client (0 = disabled)",
    )
    global_window_seconds: int = Field(
        default=60,
        description="Global limit time window in seconds",
    )

    # Backend configuration
    backend: str = Field(
        default="memory",
        description="Rate limit backend: 'memory' or 'redis'",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for 'redis' backend",
    )

    # Behavior
    include_headers: bool = Field(
        default=True,
        description="Include X-RateLimit-* headers in responses",
    )

    class Config:
        env_prefix = "MYFY_RATELIMIT_"
