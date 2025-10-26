"""
Hello World example for myfy framework.

Demonstrates:
- Configuration with settings
- Dependency injection with @provider
- Web routes with @route decorators
- Request handling with DI
- Request-scoped and singleton services
"""

from pydantic import Field

from myfy.core import REQUEST, SINGLETON, Application, BaseSettings, provider
from myfy.web import WebModule, route


# 1. Configuration
class AppSettings(BaseSettings):
    """Application settings."""

    app_name: str = Field(default="Hello myfy", description="Application name")
    greeting: str = Field(default="Hello", description="Default greeting")


# 2. Services with DI
class GreetingService:
    """A simple service to demonstrate DI."""

    def __init__(self, settings: AppSettings):
        self.settings = settings

    def greet(self, name: str) -> str:
        return f"{self.settings.greeting}, {name}!"


@provider(scope=SINGLETON)
def greeting_service(settings: AppSettings) -> GreetingService:
    """Provide greeting service as singleton."""
    return GreetingService(settings)


class RequestCounter:
    """Request-scoped service to demonstrate request scope."""

    def __init__(self):
        self.count = 0

    def increment(self) -> int:
        self.count += 1
        return self.count


class GlobalCounter:
    """Global-scoped service to demonstrate global scope."""

    def __init__(self):
        self.count = 0

    def increment(self) -> int:
        self.count += 1
        return self.count


@provider(scope=SINGLETON)
def global_counter() -> GlobalCounter:
    """Provide global counter (singleton instance)."""
    return GlobalCounter()


@provider(scope=REQUEST)
def request_counter() -> RequestCounter:
    """Provide request counter (new instance per request)."""
    return RequestCounter()


# 3. Routes with DI
@route.get("/")
async def index() -> dict:
    """Root endpoint."""
    return {
        "message": "Welcome to myfy!",
        "endpoints": [
            {"path": "/", "description": "This endpoint"},
            {"path": "/greet/{name}", "description": "Personalized greeting"},
            {"path": "/count", "description": "Request counter demo"},
            {"path": "/echo", "description": "Echo POST body"},
        ],
    }


@route.get("/greet/{name}")
async def greet(name: str, service: GreetingService) -> dict:
    """
    Greet someone by name.

    Demonstrates:
    - Path parameters
    - Singleton service injection
    """
    return {"greeting": service.greet(name)}


@route.get("/count")
async def count(counter: RequestCounter) -> dict:
    """
    Increment and return request counter.

    Demonstrates:
    - Request-scoped service injection
    - Multiple calls in same request share the same counter
    """
    count1 = counter.increment()
    count2 = counter.increment()
    return {
        "count1": count1,
        "count2": count2,
        "message": "Same request counter incremented twice",
    }


@route.get("/global-count")
async def global_count(counter: GlobalCounter) -> dict:
    """
    Increment and return global counter.

    Demonstrates:
    - Global-scoped service injection
    - Multiple calls across requests share the same counter
    """
    count1 = counter.increment()
    return {
        "count1": count1,
        "message": "Global counter incremented",
    }


@route.post("/echo")
async def echo(body: dict) -> dict:
    """
    Echo POST body back.

    Demonstrates:
    - POST requests
    - Automatic JSON body parsing
    """
    return {"received": body, "keys": list(body.keys())}


@route.get("/health")
async def health(settings: AppSettings) -> dict:
    """Health check endpoint."""
    return {"status": "ok", "app": settings.app_name}


# 4. Application setup
# Note: auto_discover=False to avoid loading web_module twice (once via entry point, once manually)
app = Application(settings_class=AppSettings, auto_discover=False)
app.add_module(WebModule())


# 5. Main entry point (optional - CLI can auto-discover)
if __name__ == "__main__":
    import asyncio

    asyncio.run(app.run())
