"""
End-to-end tests for full myfy application.

These tests verify:
- Complete application initialization
- Full HTTP request/response cycle
- Module lifecycle integration
- DI across the entire stack
"""

from typing import cast

import pytest
from starlette.testclient import TestClient

from myfy.core import Application
from myfy.core.config import BaseSettings
from myfy.core.di import REQUEST, SINGLETON, Container
from myfy.core.di.provider import clear_pending_providers, provider
from myfy.core.kernel import Module
from myfy.web import WebModule
from myfy.web.routing import Router

pytestmark = pytest.mark.e2e


# =============================================================================
# Test Application Components
# =============================================================================


class E2ESettings(BaseSettings):
    """Settings for e2e test application."""

    app_name: str = "E2E Test App"
    greeting: str = "Hello"
    debug: bool = True

    model_config = {"env_prefix": "E2E_TEST_"}


class GreetingService:
    """Service that generates greetings."""

    def __init__(self, settings: E2ESettings):
        self.settings = settings

    def greet(self, name: str) -> str:
        return f"{self.settings.greeting}, {name}!"


class CounterService:
    """Request-scoped counter service."""

    def __init__(self):
        self.count = 0

    def increment(self) -> int:
        self.count += 1
        return self.count


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def clean_providers():
    """Ensure providers are cleaned between tests."""
    clear_pending_providers()
    yield
    clear_pending_providers()


@pytest.fixture
def e2e_router() -> Router:
    """Create a fresh router for e2e tests."""
    return Router()


@pytest.fixture
def e2e_app(e2e_router: Router) -> Application:
    """Create a fully configured e2e test application."""

    # Register providers
    @provider(scope=SINGLETON)
    def greeting_service(settings: E2ESettings) -> GreetingService:
        return GreetingService(settings)

    @provider(scope=REQUEST)
    def counter_service() -> CounterService:
        return CounterService()

    # Register routes on the test router
    @e2e_router.get("/health")
    async def health():
        return {"status": "ok"}

    @e2e_router.get("/greet/{name}")
    async def greet(name: str, service: GreetingService):
        return {"message": service.greet(name)}

    @e2e_router.get("/settings")
    async def get_settings(settings: E2ESettings):
        return {"app_name": settings.app_name, "debug": settings.debug}

    @e2e_router.post("/echo")
    async def echo(data: dict):
        return {"received": data}

    @e2e_router.get("/counter")
    async def get_counter(counter: CounterService):
        return {"count": counter.increment()}

    @e2e_router.get("/error")
    async def raise_error():
        raise ValueError("Intentional test error")

    # Create application
    app = Application(settings_class=E2ESettings, auto_discover=False)
    app.add_module(WebModule(router=e2e_router))

    return app


@pytest.fixture
def test_client(e2e_app: Application) -> TestClient:
    """Create a test client for the e2e application."""
    e2e_app.initialize()

    # Get ASGI app
    web_module = e2e_app.get_module(WebModule)
    asgi_app = web_module.get_asgi_app(e2e_app.container)

    return TestClient(asgi_app.app)


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealthCheck:
    """Test basic health check endpoint."""

    def test_health_endpoint_returns_ok(self, test_client: TestClient):
        """Test that health endpoint returns 200 OK."""
        response = test_client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# =============================================================================
# DI Integration Tests
# =============================================================================


class TestDIIntegration:
    """Test DI integration through HTTP requests."""

    def test_singleton_service_injection(self, test_client: TestClient):
        """Test that singleton services are properly injected."""
        response = test_client.get("/greet/World")

        assert response.status_code == 200
        assert response.json()["message"] == "Hello, World!"

    def test_settings_injection(self, test_client: TestClient):
        """Test that settings are properly injected."""
        response = test_client.get("/settings")

        assert response.status_code == 200
        data = response.json()
        assert data["app_name"] == "E2E Test App"
        assert data["debug"] is True

    def test_request_scoped_service_isolation(self, test_client: TestClient):
        """Test that request-scoped services are isolated per request."""
        # Each request should get a fresh counter
        response1 = test_client.get("/counter")
        response2 = test_client.get("/counter")
        response3 = test_client.get("/counter")

        # Each request gets count=1 because counter is request-scoped
        assert response1.json()["count"] == 1
        assert response2.json()["count"] == 1
        assert response3.json()["count"] == 1


# =============================================================================
# Request Body Tests
# =============================================================================


class TestRequestBody:
    """Test request body handling."""

    def test_json_body_parsing(self, test_client: TestClient):
        """Test that JSON body is properly parsed."""
        payload = {"key": "value", "number": 42}
        response = test_client.post("/echo", json=payload)

        assert response.status_code == 200
        assert response.json()["received"] == payload

    def test_empty_body_handling(self, test_client: TestClient):
        """Test handling of empty request body."""
        response = test_client.post("/echo", json={})

        assert response.status_code == 200
        assert response.json()["received"] == {}


# =============================================================================
# Path Parameter Tests
# =============================================================================


class TestPathParameters:
    """Test path parameter handling."""

    def test_string_path_parameter(self, test_client: TestClient):
        """Test string path parameter."""
        response = test_client.get("/greet/Alice")

        assert response.status_code == 200
        assert "Alice" in response.json()["message"]

    def test_path_parameter_with_special_chars(self, test_client: TestClient):
        """Test path parameter with URL-encoded special characters."""
        response = test_client.get("/greet/John%20Doe")

        assert response.status_code == 200
        assert "John Doe" in response.json()["message"]


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling in full application context."""

    def test_handler_error_returns_500(self, test_client: TestClient):
        """Test that handler errors return 500."""
        response = test_client.get("/error")

        assert response.status_code == 500

    def test_404_for_unknown_route(self, test_client: TestClient):
        """Test that unknown routes return 404."""
        response = test_client.get("/nonexistent")

        assert response.status_code == 404


# =============================================================================
# Module Lifecycle Tests
# =============================================================================


class TestModuleLifecycle:
    """Test module lifecycle in e2e context."""

    @pytest.mark.asyncio
    async def test_lifespan_starts_and_stops_modules(self, e2e_router: Router):
        """Test that lifespan properly manages module lifecycle."""
        started = []
        stopped = []

        class TrackingModule:
            @property
            def name(self) -> str:
                return "tracking"

            def configure(self, container: Container) -> None:
                pass

            async def start(self) -> None:
                started.append("tracking")

            async def stop(self) -> None:
                stopped.append("tracking")

        clear_pending_providers()

        app = Application(settings_class=E2ESettings, auto_discover=False)
        app.add_module(WebModule(router=e2e_router))
        app.add_module(cast("Module", TrackingModule()))
        app.initialize()

        lifespan = app.create_lifespan()

        assert len(started) == 0
        assert len(stopped) == 0

        async with lifespan(None):
            assert "tracking" in started
            assert len(stopped) == 0

        assert "tracking" in stopped


# =============================================================================
# Multiple Modules Tests
# =============================================================================


class TestMultipleModules:
    """Test applications with multiple modules."""

    def test_app_with_multiple_custom_modules(self, e2e_router: Router):
        """Test application with multiple custom modules."""
        configure_order = []

        class ModuleA:
            @property
            def name(self) -> str:
                return "module_a"

            def configure(self, container: Container) -> None:
                configure_order.append("a")

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass

        class ModuleB:
            @property
            def name(self) -> str:
                return "module_b"

            @property
            def requires(self) -> list[type]:
                return [ModuleA]

            def configure(self, container: Container) -> None:
                configure_order.append("b")

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass

        clear_pending_providers()

        app = Application(settings_class=E2ESettings, auto_discover=False)
        app.add_module(cast("Module", ModuleB()))  # Add B first
        app.add_module(cast("Module", ModuleA()))  # Then A
        app.add_module(WebModule(router=e2e_router))

        app.initialize()

        # A should be configured before B due to dependency
        assert configure_order.index("a") < configure_order.index("b")


# =============================================================================
# Container Override Tests
# =============================================================================


class TestContainerOverrides:
    """Test container overrides in e2e context."""

    def test_override_service_in_test(self, e2e_router: Router):
        """Test that services can be overridden for testing."""
        clear_pending_providers()

        class FakeGreetingService:
            def greet(self, name: str) -> str:
                return f"Mocked greeting for {name}"

        @provider(scope=SINGLETON)
        def greeting_service(settings: E2ESettings) -> GreetingService:
            return GreetingService(settings)

        @e2e_router.get("/greet/{name}")
        async def greet(name: str, service: GreetingService):
            return {"message": service.greet(name)}

        app = Application(settings_class=E2ESettings, auto_discover=False)
        app.add_module(WebModule(router=e2e_router))
        app.initialize()

        web_module = app.get_module(WebModule)
        asgi_app = web_module.get_asgi_app(app.container)

        # Test with override
        with app.container.override({GreetingService: lambda: FakeGreetingService()}):
            client = TestClient(asgi_app.app)
            response = client.get("/greet/Test")

            assert response.status_code == 200
            assert "Mocked" in response.json()["message"]


# =============================================================================
# Concurrent Request Tests
# =============================================================================


class TestConcurrentRequests:
    """Test handling of concurrent requests."""

    def test_concurrent_requests_isolated(self, test_client: TestClient):
        """Test that concurrent requests have isolated scopes."""
        import concurrent.futures

        results = []

        def make_request(n):
            response = test_client.get(f"/greet/User{n}")
            return response.json()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        # All requests should succeed with correct greetings
        assert len(results) == 10
        for i, result in enumerate(results):
            assert "Hello," in result["message"]
