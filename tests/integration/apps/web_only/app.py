"""
Web-only example application.

A minimal application using only WebModule to verify:
- Route registration and matching
- Handler execution with DI
- Request/response cycle
- Error handling
- Singleton and request-scoped services
"""

from myfy.core import Application
from myfy.core.config import BaseSettings
from myfy.core.di import REQUEST, SINGLETON
from myfy.core.di.provider import provider
from myfy.web import WebModule
from myfy.web.routing import Router


# =============================================================================
# Settings
# =============================================================================


class WebOnlySettings(BaseSettings):
    """Settings for web-only test application."""

    app_name: str = "Web Only Test App"
    version: str = "1.0.0"
    debug: bool = True

    model_config = {"env_prefix": "WEB_ONLY_TEST_"}


# =============================================================================
# Services
# =============================================================================


class GreetingService:
    """Singleton service that generates greetings."""

    def __init__(self, settings: WebOnlySettings):
        self.settings = settings

    def greet(self, name: str) -> str:
        return f"Hello from {self.settings.app_name}, {name}!"

    def get_version(self) -> str:
        return self.settings.version


class RequestCounter:
    """Request-scoped counter to verify scope isolation."""

    def __init__(self):
        self.count = 0

    def increment(self) -> int:
        self.count += 1
        return self.count


# =============================================================================
# Application Factory
# =============================================================================


def create_app() -> tuple[Application, Router]:
    """
    Create the web-only test application.

    Returns:
        Tuple of (Application, Router) for test access.
    """
    router = Router()

    # Register providers
    @provider(scope=SINGLETON)
    def greeting_service(settings: WebOnlySettings) -> GreetingService:
        return GreetingService(settings)

    @provider(scope=REQUEST)
    def request_counter() -> RequestCounter:
        return RequestCounter()

    # =============================================================================
    # Routes
    # =============================================================================

    @router.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok"}

    @router.get("/version")
    async def version(settings: WebOnlySettings):
        """Return application version from settings."""
        return {"app": settings.app_name, "version": settings.version}

    @router.get("/greet/{name}")
    async def greet(name: str, service: GreetingService):
        """Greet a user using the singleton service."""
        return {"message": service.greet(name)}

    @router.post("/echo")
    async def echo(data: dict):
        """Echo back the request body."""
        return {"received": data}

    @router.get("/counter")
    async def counter(counter: RequestCounter):
        """
        Increment and return request-scoped counter.

        Each request should get count=1 because counter is request-scoped.
        """
        return {"count": counter.increment()}

    @router.get("/counter/double")
    async def counter_double(counter: RequestCounter):
        """
        Increment counter twice in same request.

        Should return count=2 because same request scope.
        """
        counter.increment()
        return {"count": counter.increment()}

    @router.get("/error/value")
    async def raise_value_error():
        """Raise a ValueError to test error handling."""
        raise ValueError("Intentional test error")

    @router.get("/error/runtime")
    async def raise_runtime_error():
        """Raise a RuntimeError to test error handling."""
        raise RuntimeError("Intentional runtime error")

    # Create application
    app = Application(settings_class=WebOnlySettings, auto_discover=False)
    app.add_module(WebModule(router=router))

    return app, router
