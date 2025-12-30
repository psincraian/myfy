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

Authentication:
    from myfy.web.auth import AuthModule, Anonymous, Authenticated
    from dataclasses import dataclass

    @dataclass
    class User(Authenticated):
        email: str

    def my_auth(request: Request) -> User | None:
        token = request.headers.get("Authorization")
        if not token:
            return None  # -> 401
        return User(id="123", email="user@example.com")

    app.add_module(AuthModule(authenticated_provider=my_auth))

    @route.get("/profile")
    async def profile(user: User) -> dict:
        return {"id": user.id, "email": user.email}
"""

from . import errors
from .asgi import ASGIApp
from .auth import Anonymous, Authenticated, AuthModule
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
    "Anonymous",
    "AuthModule",
    "Authenticated",
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
