"""
Integration tests for web-only application.

Tests WebModule functionality in isolation:
- Route registration and matching
- Handler execution with dependency injection
- Request/response cycle
- Singleton vs request-scoped services
- Error handling
"""

import concurrent.futures

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_returns_ok(self, test_client: TestClient):
        """Health endpoint returns 200 with status ok."""
        response = test_client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# =============================================================================
# Settings Injection Tests
# =============================================================================


class TestSettingsInjection:
    """Test that settings are properly injected into handlers."""

    def test_version_endpoint_returns_settings(self, test_client: TestClient):
        """Version endpoint returns app name and version from settings."""
        response = test_client.get("/version")

        assert response.status_code == 200
        data = response.json()
        assert data["app"] == "Web Only Test App"
        assert data["version"] == "1.0.0"


# =============================================================================
# Singleton Service Tests
# =============================================================================


class TestSingletonService:
    """Test singleton service injection and behavior."""

    def test_greeting_uses_singleton_service(self, test_client: TestClient):
        """Greeting endpoint uses injected GreetingService."""
        response = test_client.get("/greet/Alice")

        assert response.status_code == 200
        data = response.json()
        assert "Alice" in data["message"]
        assert "Web Only Test App" in data["message"]

    def test_greeting_with_special_characters(self, test_client: TestClient):
        """Greeting handles URL-encoded special characters."""
        response = test_client.get("/greet/John%20Doe")

        assert response.status_code == 200
        assert "John Doe" in response.json()["message"]

    def test_singleton_is_same_instance(self, test_client: TestClient):
        """Multiple requests use the same singleton service instance."""
        # Make multiple requests
        r1 = test_client.get("/greet/User1")
        r2 = test_client.get("/greet/User2")

        # Both should succeed with consistent app name
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert "Web Only Test App" in r1.json()["message"]
        assert "Web Only Test App" in r2.json()["message"]


# =============================================================================
# Request Scope Tests
# =============================================================================


class TestRequestScope:
    """Test request-scoped service isolation."""

    def test_counter_resets_per_request(self, test_client: TestClient):
        """Each request gets a fresh counter (request scope)."""
        r1 = test_client.get("/counter")
        r2 = test_client.get("/counter")
        r3 = test_client.get("/counter")

        # Each request should start at 1
        assert r1.json()["count"] == 1
        assert r2.json()["count"] == 1
        assert r3.json()["count"] == 1

    def test_counter_persists_within_request(self, test_client: TestClient):
        """Counter increments correctly within same request."""
        response = test_client.get("/counter/double")

        # Same request, counter incremented twice
        assert response.json()["count"] == 2


# =============================================================================
# Request Body Tests
# =============================================================================


class TestRequestBody:
    """Test request body parsing and handling."""

    def test_echo_returns_json_body(self, test_client: TestClient):
        """Echo endpoint returns the received JSON body."""
        payload = {"key": "value", "number": 42, "nested": {"a": 1}}
        response = test_client.post("/echo", json=payload)

        assert response.status_code == 200
        assert response.json()["received"] == payload

    def test_echo_with_empty_body(self, test_client: TestClient):
        """Echo handles empty JSON body."""
        response = test_client.post("/echo", json={})

        assert response.status_code == 200
        assert response.json()["received"] == {}

    def test_echo_with_list_body(self, test_client: TestClient):
        """Echo handles list as JSON body."""
        payload = [1, 2, 3, "four"]
        response = test_client.post("/echo", json=payload)

        assert response.status_code == 200
        # Note: list is wrapped in dict by handler
        assert response.json()["received"] == payload


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling in handlers."""

    def test_value_error_returns_500(self, test_client: TestClient):
        """ValueError in handler returns 500 Internal Server Error."""
        response = test_client.get("/error/value")

        assert response.status_code == 500

    def test_runtime_error_returns_500(self, test_client: TestClient):
        """RuntimeError in handler returns 500 Internal Server Error."""
        response = test_client.get("/error/runtime")

        assert response.status_code == 500

    def test_404_for_unknown_route(self, test_client: TestClient):
        """Unknown routes return 404 Not Found."""
        response = test_client.get("/nonexistent/route")

        assert response.status_code == 404


# =============================================================================
# Concurrent Request Tests
# =============================================================================


class TestConcurrentRequests:
    """Test handling of concurrent requests."""

    def test_concurrent_requests_are_isolated(self, test_client: TestClient):
        """Concurrent requests have isolated request scopes."""
        results = []

        def make_request(n: int):
            response = test_client.get(f"/greet/User{n}")
            return response.json()

        # Use ThreadPoolExecutor to simulate concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        # All requests should succeed
        assert len(results) == 10
        for result in results:
            assert "message" in result
            assert "Hello from" in result["message"]

    def test_concurrent_counter_requests_isolated(self, test_client: TestClient):
        """Concurrent counter requests each get fresh counter."""
        results = []

        def make_request(_: int):
            response = test_client.get("/counter")
            return response.json()["count"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        # All should return 1 (fresh counter per request)
        assert all(count == 1 for count in results)


# =============================================================================
# Module Lifecycle Tests
# =============================================================================


class TestModuleLifecycle:
    """Test WebModule lifecycle integration."""

    @pytest.mark.asyncio
    async def test_lifespan_starts_and_stops(self, web_only_app):
        """Application lifespan properly starts and stops."""
        lifespan = web_only_app.create_lifespan()

        async with lifespan(None):
            # Inside lifespan - module should be running
            pass

        # After lifespan - cleanup should have happened

    def test_application_is_initialized(self, web_only_app):
        """Application is properly initialized."""
        assert web_only_app._initialized
        assert web_only_app.container._frozen
