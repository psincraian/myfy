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

Exception Handling:
    from myfy.web import abort, errors

    # Using abort() for quick errors
    abort(404, "User not found")

    # Using errors namespace
    raise errors.NotFound("User not found")
    raise errors.BadRequest("Invalid email", field="email")

    # Custom exceptions (import from exceptions module)
    from myfy.web.exceptions import WebError

    class CustomError(WebError):
        status_code = 418
        error_type = "teapot"

Rate Limiting:
    from myfy.web.ratelimit import RateLimitModule, rate_limit, RateLimitKey

    @route.get("/api/data")
    @rate_limit(100)  # 100 requests per minute per IP
    async def get_data() -> dict:
        ...

    @route.get("/api/profile")
    @rate_limit(50, key=RateLimitKey.USER)  # By authenticated user
    async def get_profile(user: User) -> Profile:
        ...
"""

from . import errors
from .asgi import ASGIApp
from .config import WebSettings
from .context import RequestContext, get_request_context
from .extensions import IMiddlewareProvider, IWebExtension
from .factory import create_asgi_app_with_lifespan
from .module import WebModule, web_module
from .params import Query, QueryParam
from .routing import HTTPMethod, Route, Router, route
from .shortcuts import abort
from .version import __version__

__all__ = [
    "ASGIApp",
    "HTTPMethod",
    "IMiddlewareProvider",
    "IWebExtension",
    "Query",
    "QueryParam",
    "RequestContext",
    "Route",
    "Router",
    "WebModule",
    "WebSettings",
    "__version__",
    "abort",
    "create_asgi_app_with_lifespan",
    "errors",
    "get_request_context",
    "route",
    "web_module",
]
