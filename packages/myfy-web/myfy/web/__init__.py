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
    The framework provides centralized exception handling through domain
    exceptions that automatically map to HTTP status codes:

    from myfy.web import NotFoundException, ValidationException

    @route.get("/users/{user_id}")
    async def get_user(user_id: int, db: Database) -> dict:
        user = await db.get_user(user_id)
        if not user:
            raise NotFoundException(resource_type="User", resource_id=user_id)
        return user

    Custom exception handlers can be registered:

    from myfy.web import exception_handlers

    @exception_handlers.handler(MyCustomException)
    async def handle_custom(request, exc):
        return JSONResponse(status_code=400, content={"error": str(exc)})
"""

from .asgi import ASGIApp
from .config import WebSettings
from .context import RequestContext, get_request_context
from .exception_handlers import ExceptionHandlerRegistry, exception_handlers
from .exceptions import (
    ConflictException,
    ForbiddenException,
    GoneException,
    HTTPMappedException,
    NotFoundException,
    ServiceUnavailableException,
    TooManyRequestsException,
    UnauthorizedException,
    UnprocessableEntityException,
    ValidationException,
)
from .extensions import IMiddlewareProvider, IWebExtension
from .factory import create_asgi_app_with_lifespan
from .module import WebModule, web_module
from .routing import HTTPMethod, Route, Router, route
from .version import __version__

__all__ = [
    # ASGI
    "ASGIApp",
    # Exceptions
    "ConflictException",
    "ExceptionHandlerRegistry",
    "ForbiddenException",
    "GoneException",
    "HTTPMappedException",
    "NotFoundException",
    "ServiceUnavailableException",
    "TooManyRequestsException",
    "UnauthorizedException",
    "UnprocessableEntityException",
    "ValidationException",
    "exception_handlers",
    # Extensions
    "IMiddlewareProvider",
    "IWebExtension",
    # Routing
    "HTTPMethod",
    "Route",
    "Router",
    "route",
    # Context
    "RequestContext",
    "get_request_context",
    # Module
    "WebModule",
    "WebSettings",
    "web_module",
    # Factory
    "create_asgi_app_with_lifespan",
    # Version
    "__version__",
]
