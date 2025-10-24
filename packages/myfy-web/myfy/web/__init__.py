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

from .routing import Router, route, Route, HTTPMethod
from .module import WebModule, web_module
from .context import RequestContext, get_request_context
from .asgi import ASGIApp
from .config import WebSettings

__all__ = [
    # Routing
    "Router",
    "route",
    "Route",
    "HTTPMethod",
    # Module
    "WebModule",
    "web_module",
    # Context
    "RequestContext",
    "get_request_context",
    # ASGI
    "ASGIApp",
    # Config
    "WebSettings",
]
