"""
Rate limiting for myfy web framework.

Provides flexible rate limiting with:
- Global protection via middleware
- Per-route customization via decorator
- Key override for dynamic rate limiting

Usage:
    from myfy.web.ratelimit import RateLimitKey, rate_limit

    # Simple rate limiting with preset key
    @route.get("/api/data")
    @rate_limit(100)  # 100 requests per minute, keyed by IP
    async def get_data() -> dict:
        ...

    # Rate limit by authenticated user
    @route.get("/api/profile")
    @rate_limit(50, key=RateLimitKey.USER)
    async def get_profile(user: User) -> Profile:
        ...

    # Dynamic key override in handler
    @route.get("/api/org/{org_id}/data")
    @rate_limit(100)
    async def get_org_data(org: Organization, rl: RateLimitContext) -> OrgData:
        rl.override_key(f"org:{org.id}:tier:{org.tier}")
        ...
"""

from .config import RateLimitSettings
from .context import RateLimitContext
from .decorator import rate_limit
from .keys import RateLimitKey
from .middleware import RateLimitMiddleware
from .module import RateLimitModule
from .store import InMemoryRateLimitStore, RateLimitStore
from .types import RateLimitConfig, RateLimitResult

__all__ = [
    "InMemoryRateLimitStore",
    "RateLimitConfig",
    "RateLimitContext",
    "RateLimitKey",
    "RateLimitMiddleware",
    "RateLimitModule",
    "RateLimitResult",
    "RateLimitSettings",
    "RateLimitStore",
    "rate_limit",
]
