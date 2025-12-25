"""
Integration tests for rate limiting middleware.

These tests verify the complete rate limiting flow with ASGI app.
"""

import pytest
from starlette.testclient import TestClient

from myfy.core.di import SINGLETON, Container
from myfy.web.asgi import ASGIApp
from myfy.web.ratelimit import (
    InMemoryRateLimitStore,
    RateLimitKey,
    RateLimitSettings,
    rate_limit,
)
from myfy.web.routing import Router

pytestmark = pytest.mark.integration


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def router():
    """Create a fresh router for each test."""
    return Router()


@pytest.fixture
def store():
    """Create a fresh rate limit store for each test."""
    return InMemoryRateLimitStore()


@pytest.fixture
def settings():
    """Create test settings with low limits for fast testing."""
    return RateLimitSettings(
        enabled=True,
        default_requests=5,
        default_window_seconds=60,
        global_requests=10,
        global_window_seconds=60,
        include_headers=True,
    )


# =============================================================================
# Global Rate Limiting Tests
# =============================================================================


class TestGlobalRateLimiting:
    """Verify global rate limiting via middleware."""

    def test_requests_allowed_until_global_limit(self, router, store, settings):
        """Requests are allowed until global limit is reached."""

        # Register a simple route
        @router.get("/api/data")
        async def get_data():
            return {"data": "value"}

        # Create app with rate limiting
        container = Container()
        container.register(type_=Router, factory=lambda: router, scope=SINGLETON)
        container.compile()

        app = ASGIApp(container, router)

        # Add middleware manually for testing
        from myfy.web.ratelimit.middleware import RateLimitMiddleware

        app.app.add_middleware(RateLimitMiddleware, store=store, settings=settings)

        client = TestClient(app.app)

        # First 10 requests should succeed (global limit)
        for i in range(10):
            response = client.get("/api/data")
            assert response.status_code == 200, f"Request {i + 1} should succeed"
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers

        # 11th request should be rate limited
        response = client.get("/api/data")
        assert response.status_code == 429
        assert response.json()["type"] == "rate_limit_exceeded"
        assert "Retry-After" in response.headers

    def test_rate_limit_headers_present(self, router, store, settings):
        """Rate limit headers are included in responses."""

        @router.get("/api/data")
        async def get_data():
            return {"data": "value"}

        container = Container()
        container.register(type_=Router, factory=lambda: router, scope=SINGLETON)
        container.compile()

        app = ASGIApp(container, router)

        from myfy.web.ratelimit.middleware import RateLimitMiddleware

        app.app.add_middleware(RateLimitMiddleware, store=store, settings=settings)

        client = TestClient(app.app)
        response = client.get("/api/data")

        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "10"  # global limit
        assert response.headers["X-RateLimit-Remaining"] == "9"
        assert "X-RateLimit-Reset" in response.headers

    def test_rate_limiting_disabled(self, router, store):
        """Rate limiting can be disabled globally."""
        settings = RateLimitSettings(enabled=False)

        @router.get("/api/data")
        async def get_data():
            return {"data": "value"}

        container = Container()
        container.register(type_=Router, factory=lambda: router, scope=SINGLETON)
        container.compile()

        app = ASGIApp(container, router)

        from myfy.web.ratelimit.middleware import RateLimitMiddleware

        app.app.add_middleware(RateLimitMiddleware, store=store, settings=settings)

        client = TestClient(app.app)

        # All requests should succeed even beyond normal limit
        for _ in range(20):
            response = client.get("/api/data")
            assert response.status_code == 200


# =============================================================================
# Key Strategy Tests
# =============================================================================


class TestKeyStrategies:
    """Verify different key strategies work correctly."""

    def test_ip_based_rate_limiting(self, router, store, settings):
        """Different IPs have independent rate limits."""

        @router.get("/api/data")
        async def get_data():
            return {"data": "value"}

        container = Container()
        container.register(type_=Router, factory=lambda: router, scope=SINGLETON)
        container.compile()

        app = ASGIApp(container, router)

        from myfy.web.ratelimit.middleware import RateLimitMiddleware

        app.app.add_middleware(RateLimitMiddleware, store=store, settings=settings)

        client = TestClient(app.app)

        # Exhaust limit for "client A" (simulated via X-Forwarded-For)
        for _ in range(10):
            response = client.get("/api/data", headers={"X-Forwarded-For": "1.2.3.4"})
            assert response.status_code == 200

        # Client A should be rate limited
        response = client.get("/api/data", headers={"X-Forwarded-For": "1.2.3.4"})
        assert response.status_code == 429

        # Client B should still have quota
        response = client.get("/api/data", headers={"X-Forwarded-For": "5.6.7.8"})
        assert response.status_code == 200

    def test_api_key_based_rate_limiting(self, router, store):
        """Rate limiting by API key header."""
        settings = RateLimitSettings(
            enabled=True,
            default_key=RateLimitKey.API_KEY,
            global_requests=5,
            global_window_seconds=60,
        )

        @router.get("/api/data")
        async def get_data():
            return {"data": "value"}

        container = Container()
        container.register(type_=Router, factory=lambda: router, scope=SINGLETON)
        container.compile()

        app = ASGIApp(container, router)

        from myfy.web.ratelimit.middleware import RateLimitMiddleware

        app.app.add_middleware(RateLimitMiddleware, store=store, settings=settings)

        client = TestClient(app.app)

        # Exhaust limit for API key A
        for _ in range(5):
            response = client.get("/api/data", headers={"X-API-Key": "key-a"})
            assert response.status_code == 200

        # API key A should be rate limited
        response = client.get("/api/data", headers={"X-API-Key": "key-a"})
        assert response.status_code == 429

        # API key B should still have quota
        response = client.get("/api/data", headers={"X-API-Key": "key-b"})
        assert response.status_code == 200


# =============================================================================
# Decorator Integration Tests
# =============================================================================


class TestDecoratorIntegration:
    """Verify @rate_limit decorator integration."""

    def test_decorated_handler_has_config(self, router):
        """Decorated handlers have rate limit config attached."""
        from myfy.web.ratelimit.decorator import get_rate_limit_config

        @router.get("/api/data")
        @rate_limit(100, window_seconds=60)
        async def get_data():
            return {"data": "value"}

        routes = router.get_routes()
        assert len(routes) == 1

        config = get_rate_limit_config(routes[0].handler)
        assert config is not None
        assert config.requests == 100
        assert config.window_seconds == 60

    def test_undecorated_handler_no_config(self, router):
        """Undecorated handlers have no rate limit config."""
        from myfy.web.ratelimit.decorator import get_rate_limit_config

        @router.get("/api/data")
        async def get_data():
            return {"data": "value"}

        routes = router.get_routes()
        config = get_rate_limit_config(routes[0].handler)
        assert config is None


# =============================================================================
# 429 Response Format Tests
# =============================================================================


class TestRateLimitResponse:
    """Verify rate limit error response format."""

    def test_429_response_format(self, router, store, settings):
        """Rate limit error follows RFC 7807 Problem Details format."""

        @router.get("/api/data")
        async def get_data():
            return {"data": "value"}

        container = Container()
        container.register(type_=Router, factory=lambda: router, scope=SINGLETON)
        container.compile()

        app = ASGIApp(container, router)

        from myfy.web.ratelimit.middleware import RateLimitMiddleware

        app.app.add_middleware(RateLimitMiddleware, store=store, settings=settings)

        client = TestClient(app.app)

        # Exhaust limit
        for _ in range(10):
            client.get("/api/data")

        # Check error response format
        response = client.get("/api/data")
        assert response.status_code == 429

        body = response.json()
        assert body["type"] == "rate_limit_exceeded"
        assert body["title"] == "Rate Limit Exceeded"
        assert body["status"] == 429
        assert "detail" in body
        assert "retry_after" in body
        assert isinstance(body["retry_after"], int)
        assert body["retry_after"] > 0
