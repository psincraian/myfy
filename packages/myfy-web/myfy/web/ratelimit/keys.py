"""
Rate limit key strategies.

Defines preset strategies for identifying clients for rate limiting.
"""

from enum import Enum


class RateLimitKey(str, Enum):
    """
    Preset strategies for rate limit key extraction.

    These presets cover common use cases. For custom key logic,
    use RateLimitContext.override_key() in the handler.

    Attributes:
        IP: Rate limit by client IP address (default)
        USER: Rate limit by authenticated user ID (requires auth)
        API_KEY: Rate limit by X-API-Key header
        SESSION: Rate limit by session ID cookie
        ENDPOINT: Rate limit by IP + path (per-endpoint per-client)
        GLOBAL: Single shared limit for all requests (use for expensive operations)
    """

    IP = "ip"
    USER = "user"
    API_KEY = "api_key"
    SESSION = "session"
    ENDPOINT = "endpoint"
    GLOBAL = "global"

    def __str__(self) -> str:
        return self.value
