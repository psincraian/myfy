"""
Request-scoped rate limit context.

Provides injectable context for dynamic key override in handlers.
"""

from contextvars import ContextVar
from dataclasses import dataclass, field

from .types import RateLimitResult

# Context variable for the current request's rate limit context
_rate_limit_context: ContextVar["RateLimitContext | None"] = ContextVar["RateLimitContext | None"](
    "_rate_limit_context", default=None
)


@dataclass
class RateLimitContext:
    """
    Request-scoped rate limit context.

    Inject this into handlers to:
    - Override the rate limit key dynamically
    - Access rate limit metadata for the current request
    - Skip rate limiting for specific requests

    Usage:
        @route.get("/api/org/{org_id}/data")
        @rate_limit(100)
        async def get_org_data(org: Organization, rl: RateLimitContext) -> OrgData:
            # Override key based on business logic
            if org.is_premium:
                rl.override_key(f"premium:org:{org.id}")
            else:
                rl.override_key(f"free:org:{org.id}")
            ...

        @route.get("/api/health")
        @rate_limit(100)
        async def health_check(rl: RateLimitContext) -> dict:
            # Skip rate limiting for health checks from internal IPs
            if is_internal_request():
                rl.skip()
            return {"status": "ok"}
    """

    # Key override (set by handler)
    _override_key: str | None = field(default=None, repr=False)

    # Skip flag (set by handler to bypass rate limiting)
    _skip: bool = field(default=False, repr=False)

    # Result from rate limit check (set by middleware/executor)
    _result: RateLimitResult | None = field(default=None, repr=False)

    # Original key (set by middleware/executor for reference)
    _original_key: str | None = field(default=None, repr=False)

    def override_key(self, key: str) -> None:
        """
        Override the rate limit key for this request.

        Call this early in the handler to use a different key
        than the default strategy specified in the decorator.

        The key will be used for the rate limit check. If the check
        has already been performed, this will have no effect.

        Args:
            key: The custom key to use for rate limiting

        Example:
            # Rate limit by organization instead of IP
            rl.override_key(f"org:{org.id}")

            # Rate limit by user tier
            rl.override_key(f"tier:{user.tier}:user:{user.id}")
        """
        self._override_key = key

    def skip(self) -> None:
        """
        Skip rate limiting for this request.

        Use for internal requests, health checks, or other
        requests that should bypass rate limiting.

        Example:
            if request_from_internal_network():
                rl.skip()
        """
        self._skip = True

    @property
    def key(self) -> str | None:
        """Get the effective key (override or original)."""
        return self._override_key or self._original_key

    @property
    def original_key(self) -> str | None:
        """Get the original key (before any override)."""
        return self._original_key

    @property
    def should_skip(self) -> bool:
        """Check if rate limiting should be skipped."""
        return self._skip

    @property
    def result(self) -> RateLimitResult | None:
        """Get the rate limit check result."""
        return self._result

    @property
    def remaining(self) -> int | None:
        """Get remaining requests in current window."""
        return self._result.remaining if self._result else None

    @property
    def limit(self) -> int | None:
        """Get the rate limit for this request."""
        return self._result.limit if self._result else None


def get_rate_limit_context() -> RateLimitContext | None:
    """Get the current request's rate limit context."""
    return _rate_limit_context.get()


def set_rate_limit_context(context: RateLimitContext) -> None:
    """Set the rate limit context for the current request."""
    _rate_limit_context.set(context)


def clear_rate_limit_context() -> None:
    """Clear the rate limit context after request completes."""
    _rate_limit_context.set(None)
