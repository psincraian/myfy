"""
Unit tests for the rate limiting module.

These tests verify:
- RateLimitKey enum values and behavior
- RateLimitConfig validation
- RateLimitResult properties and headers
- InMemoryRateLimitStore operations
- RateLimitContext override functionality
- rate_limit decorator metadata attachment
"""

import asyncio
import time

import pytest

from myfy.web.ratelimit import (
    InMemoryRateLimitStore,
    RateLimitConfig,
    RateLimitContext,
    RateLimitKey,
    RateLimitResult,
    rate_limit,
)
from myfy.web.ratelimit.decorator import RATE_LIMIT_ATTR, get_rate_limit_config

pytestmark = pytest.mark.unit


# =============================================================================
# RateLimitKey Tests
# =============================================================================


class TestRateLimitKey:
    """Verify RateLimitKey enum behavior."""

    def test_key_values(self):
        """All key strategies have correct string values."""
        assert RateLimitKey.IP.value == "ip"
        assert RateLimitKey.USER.value == "user"
        assert RateLimitKey.API_KEY.value == "api_key"
        assert RateLimitKey.SESSION.value == "session"
        assert RateLimitKey.ENDPOINT.value == "endpoint"
        assert RateLimitKey.GLOBAL.value == "global"

    def test_key_string_conversion(self):
        """Keys convert to strings correctly."""
        assert str(RateLimitKey.IP) == "ip"
        assert str(RateLimitKey.USER) == "user"

    def test_key_is_string_enum(self):
        """RateLimitKey is a string enum for JSON serialization."""
        assert isinstance(RateLimitKey.IP, str)
        assert RateLimitKey.IP == "ip"


# =============================================================================
# RateLimitConfig Tests
# =============================================================================


class TestRateLimitConfig:
    """Verify RateLimitConfig validation and defaults."""

    def test_basic_config(self):
        """Basic configuration with required fields."""
        config = RateLimitConfig(requests=100)
        assert config.requests == 100
        assert config.window_seconds == 60  # default
        assert config.key == RateLimitKey.IP  # default
        assert config.scope is None  # default

    def test_config_with_all_fields(self):
        """Configuration with all fields specified."""
        config = RateLimitConfig(
            requests=50,
            window_seconds=300,
            key=RateLimitKey.USER,
            scope="api",
        )
        assert config.requests == 50
        assert config.window_seconds == 300
        assert config.key == RateLimitKey.USER
        assert config.scope == "api"

    def test_config_with_string_key(self):
        """Configuration with custom string key."""
        config = RateLimitConfig(requests=100, key="custom:bucket")
        assert config.key == "custom:bucket"

    def test_config_validation_requests_positive(self):
        """Requests must be positive."""
        with pytest.raises(ValueError, match="requests must be positive"):
            RateLimitConfig(requests=0)

        with pytest.raises(ValueError, match="requests must be positive"):
            RateLimitConfig(requests=-1)

    def test_config_validation_window_positive(self):
        """Window seconds must be positive."""
        with pytest.raises(ValueError, match="window_seconds must be positive"):
            RateLimitConfig(requests=100, window_seconds=0)

        with pytest.raises(ValueError, match="window_seconds must be positive"):
            RateLimitConfig(requests=100, window_seconds=-1)

    def test_config_is_immutable(self):
        """Config is frozen (immutable)."""
        config = RateLimitConfig(requests=100)
        with pytest.raises(AttributeError):
            config.requests = 200  # type: ignore


# =============================================================================
# RateLimitResult Tests
# =============================================================================


class TestRateLimitResult:
    """Verify RateLimitResult properties and headers."""

    def test_allowed_result(self):
        """Result for allowed request."""
        result = RateLimitResult(
            allowed=True,
            remaining=99,
            reset_at=time.time() + 60,
            limit=100,
        )
        assert result.allowed is True
        assert result.remaining == 99
        assert result.retry_after == 0
        assert result.limit == 100

    def test_denied_result(self):
        """Result for denied request."""
        result = RateLimitResult(
            allowed=False,
            remaining=0,
            reset_at=time.time() + 30,
            retry_after=30,
            limit=100,
        )
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after == 30

    def test_headers_allowed(self):
        """Headers for allowed request."""
        reset_at = time.time() + 60
        result = RateLimitResult(
            allowed=True,
            remaining=99,
            reset_at=reset_at,
            limit=100,
        )
        headers = result.headers
        assert headers["X-RateLimit-Limit"] == "100"
        assert headers["X-RateLimit-Remaining"] == "99"
        assert headers["X-RateLimit-Reset"] == str(int(reset_at))
        assert "Retry-After" not in headers

    def test_headers_denied(self):
        """Headers for denied request include Retry-After."""
        reset_at = time.time() + 30
        result = RateLimitResult(
            allowed=False,
            remaining=0,
            reset_at=reset_at,
            retry_after=30,
            limit=100,
        )
        headers = result.headers
        assert headers["X-RateLimit-Limit"] == "100"
        assert headers["X-RateLimit-Remaining"] == "0"
        assert headers["Retry-After"] == "30"

    def test_headers_remaining_never_negative(self):
        """Remaining in headers is never negative."""
        result = RateLimitResult(
            allowed=False,
            remaining=-5,  # Can happen internally
            reset_at=time.time() + 30,
            limit=100,
        )
        assert result.headers["X-RateLimit-Remaining"] == "0"


# =============================================================================
# InMemoryRateLimitStore Tests
# =============================================================================


class TestInMemoryRateLimitStore:
    """Verify InMemoryRateLimitStore behavior."""

    @pytest.fixture
    def store(self):
        """Create a fresh store for each test."""
        return InMemoryRateLimitStore()

    @pytest.mark.asyncio
    async def test_first_request_allowed(self, store):
        """First request to a bucket is always allowed."""
        result = await store.check_and_increment("test:key", 10, 60)
        assert result.allowed is True
        assert result.remaining == 9
        assert result.limit == 10

    @pytest.mark.asyncio
    async def test_requests_until_limit(self, store):
        """Requests are allowed until limit is reached."""
        # Make 10 requests (limit is 10)
        for i in range(10):
            result = await store.check_and_increment("test:key", 10, 60)
            assert result.allowed is True
            assert result.remaining == 10 - i - 1

        # 11th request should be denied
        result = await store.check_and_increment("test:key", 10, 60)
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after > 0

    @pytest.mark.asyncio
    async def test_different_keys_independent(self, store):
        """Different keys have independent limits."""
        # Exhaust limit for key A
        for _ in range(5):
            await store.check_and_increment("key:a", 5, 60)

        result_a = await store.check_and_increment("key:a", 5, 60)
        assert result_a.allowed is False

        # Key B should still have full quota
        result_b = await store.check_and_increment("key:b", 5, 60)
        assert result_b.allowed is True
        assert result_b.remaining == 4

    @pytest.mark.asyncio
    async def test_window_expiration(self, store):
        """Counter resets when window expires."""
        # Use a very short window
        await store.check_and_increment("test:key", 1, 1)

        # Should be denied immediately
        result = await store.check_and_increment("test:key", 1, 1)
        assert result.allowed is False

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # Should be allowed again
        result = await store.check_and_increment("test:key", 1, 1)
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_get_remaining_no_increment(self, store):
        """get_remaining doesn't increment the counter."""
        # Make 5 requests
        for _ in range(5):
            await store.check_and_increment("test:key", 10, 60)

        # Check remaining (shouldn't increment)
        result = await store.get_remaining("test:key", 10, 60)
        assert result.remaining == 5

        # Check again - should be the same
        result = await store.get_remaining("test:key", 10, 60)
        assert result.remaining == 5

    @pytest.mark.asyncio
    async def test_reset_clears_bucket(self, store):
        """reset() clears a bucket's state."""
        # Exhaust the limit
        for _ in range(5):
            await store.check_and_increment("test:key", 5, 60)

        result = await store.check_and_increment("test:key", 5, 60)
        assert result.allowed is False

        # Reset the bucket
        await store.reset("test:key")

        # Should be allowed again with full quota
        result = await store.check_and_increment("test:key", 5, 60)
        assert result.allowed is True
        assert result.remaining == 4

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, store):
        """Store is thread-safe for concurrent requests."""
        # Make 100 concurrent requests to the same key
        tasks = [store.check_and_increment("test:key", 50, 60) for _ in range(100)]
        results = await asyncio.gather(*tasks)

        # Exactly 50 should be allowed
        allowed_count = sum(1 for r in results if r.allowed)
        denied_count = sum(1 for r in results if not r.allowed)

        assert allowed_count == 50
        assert denied_count == 50


# =============================================================================
# RateLimitContext Tests
# =============================================================================


class TestRateLimitContext:
    """Verify RateLimitContext override functionality."""

    def test_initial_state(self):
        """Context starts with no override."""
        ctx = RateLimitContext()
        assert ctx.key is None
        assert ctx.original_key is None
        assert ctx.should_skip is False
        assert ctx.result is None

    def test_override_key(self):
        """override_key sets the custom key."""
        ctx = RateLimitContext()
        ctx._original_key = "ip:192.168.1.1"

        ctx.override_key("user:123")

        assert ctx.key == "user:123"
        assert ctx.original_key == "ip:192.168.1.1"

    def test_skip(self):
        """skip() sets the skip flag."""
        ctx = RateLimitContext()
        assert ctx.should_skip is False

        ctx.skip()

        assert ctx.should_skip is True

    def test_result_properties(self):
        """Result properties delegate to stored result."""
        ctx = RateLimitContext()
        ctx._result = RateLimitResult(
            allowed=True,
            remaining=50,
            reset_at=time.time() + 60,
            limit=100,
        )

        assert ctx.remaining == 50
        assert ctx.limit == 100

    def test_result_properties_none_when_no_result(self):
        """Result properties return None when no result."""
        ctx = RateLimitContext()
        assert ctx.remaining is None
        assert ctx.limit is None


# =============================================================================
# rate_limit Decorator Tests
# =============================================================================


class TestRateLimitDecorator:
    """Verify rate_limit decorator attaches config correctly."""

    def test_basic_decorator(self):
        """Decorator attaches config with defaults."""

        @rate_limit(100)
        async def handler():
            pass

        config = get_rate_limit_config(handler)
        assert config is not None
        assert config.requests == 100
        assert config.window_seconds == 60
        assert config.key == RateLimitKey.IP

    def test_decorator_with_all_options(self):
        """Decorator attaches config with all options."""

        @rate_limit(50, window_seconds=300, key=RateLimitKey.USER, scope="api")
        async def handler():
            pass

        config = get_rate_limit_config(handler)
        assert config is not None
        assert config.requests == 50
        assert config.window_seconds == 300
        assert config.key == RateLimitKey.USER
        assert config.scope == "api"

    def test_decorator_with_string_key(self):
        """Decorator works with custom string key."""

        @rate_limit(100, key="custom:bucket")
        async def handler():
            pass

        config = get_rate_limit_config(handler)
        assert config is not None
        assert config.key == "custom:bucket"

    def test_decorator_preserves_function_metadata(self):
        """Decorator preserves function name and docstring."""

        @rate_limit(100)
        async def my_handler():
            """Handler docstring."""
            pass

        assert my_handler.__name__ == "my_handler"
        assert my_handler.__doc__ == "Handler docstring."

    def test_decorator_config_accessible_via_attribute(self):
        """Config is accessible via RATE_LIMIT_ATTR."""

        @rate_limit(100)
        async def handler():
            pass

        assert hasattr(handler, RATE_LIMIT_ATTR)
        assert getattr(handler, RATE_LIMIT_ATTR).requests == 100

    def test_get_rate_limit_config_none_for_undecorated(self):
        """get_rate_limit_config returns None for undecorated handlers."""

        async def handler():
            pass

        assert get_rate_limit_config(handler) is None

    def test_decorator_ordering_with_route(self):
        """Decorator works correctly when stacked with other decorators."""

        # Simulate @route.get decorator (simplified)
        def mock_route(func):
            func._route_info = {"method": "GET", "path": "/test"}
            return func

        @mock_route
        @rate_limit(100)
        async def handler():
            pass

        # Both decorators' metadata should be accessible
        assert hasattr(handler, "_route_info")
        config = get_rate_limit_config(handler)
        assert config is not None
        assert config.requests == 100


# =============================================================================
# RateLimitSettings Tests
# =============================================================================


class TestRateLimitSettings:
    """Verify RateLimitSettings defaults and validation."""

    def test_default_settings(self):
        """Default settings are sensible."""
        from myfy.web.ratelimit import RateLimitSettings

        settings = RateLimitSettings()
        assert settings.enabled is True
        assert settings.default_requests == 100
        assert settings.default_window_seconds == 60
        assert settings.default_key == RateLimitKey.IP
        assert settings.global_requests == 1000
        assert settings.backend == "memory"
        assert settings.include_headers is True

    def test_settings_from_env(self, monkeypatch):
        """Settings can be loaded from environment variables."""
        from myfy.web.ratelimit import RateLimitSettings

        monkeypatch.setenv("MYFY_RATELIMIT_ENABLED", "false")
        monkeypatch.setenv("MYFY_RATELIMIT_DEFAULT_REQUESTS", "200")
        monkeypatch.setenv("MYFY_RATELIMIT_GLOBAL_REQUESTS", "5000")

        settings = RateLimitSettings()
        assert settings.enabled is False
        assert settings.default_requests == 200
        assert settings.global_requests == 5000
