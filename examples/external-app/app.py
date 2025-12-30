"""
Example external application.

This demonstrates running a myfy app from a different directory
using: uv run myfy run --app-path /path/to/external-app

Usage:
    # From any directory
    uv run myfy run --app-path /path/to/examples/external-app

    # Test endpoints
    curl http://127.0.0.1:8000/
    curl http://127.0.0.1:8000/greet/world
    curl http://127.0.0.1:8000/health
"""

from myfy.core import SINGLETON, Application, provider
from myfy.web import WebModule, route


class GreetingService:
    """Simple service to demonstrate DI works."""

    def greet(self, name: str) -> str:
        return f"Hello, {name}! I'm running from an external folder."


@provider(scope=SINGLETON)
def greeting_service() -> GreetingService:
    """Provide greeting service."""
    return GreetingService()


@route.get("/")
async def home() -> dict:
    """Home endpoint."""
    return {
        "message": "External App",
        "endpoints": [
            "/",
            "/greet/{name}",
            "/health",
        ],
    }


@route.get("/greet/{name}")
async def greet(name: str, service: GreetingService) -> dict:
    """Greet endpoint with DI."""
    message = service.greet(name)
    return {"message": message}


@route.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "app": "external-app"}


# Create the application
app = Application(auto_discover=False)
app.add_module(WebModule())
