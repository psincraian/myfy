"""
myfy-web: Web/HTTP module for myfy framework.

Provides FastAPI-like routing with DI-powered handlers.

Usage:
    from myfy.web import route, WebModule
    from myfy.core import Application, provider, SINGLETON

    @provider(scope=SINGLETON)
    def database() -> Database:
        return Database()

    @route.get("/users/{user_id}")
    async def get_user(user_id: int, db: Database) -> dict:
        user = await db.get_user(user_id)
        return {"id": user.id, "name": user.name}

    app = Application()
    app.add_module(WebModule())
    await app.run()
"""

from .asgi import ASGIApp
from .config import WebSettings
from .context import RequestContext, get_request_context
from .extensions import IMiddlewareProvider, IWebExtension
from .factory import create_asgi_app_with_lifespan
from .module import WebModule, web_module
from .routing import HTTPMethod, Route, Router, route
from .version import __version__

__all__ = [
    "ASGIApp",
    "HTTPMethod",
    "IMiddlewareProvider",
    "IWebExtension",
    "RequestContext",
    "Route",
    "Router",
    "WebModule",
    "WebSettings",
    "__version__",
    "create_asgi_app_with_lifespan",
    "get_request_context",
    "route",
    "web_module",
]
