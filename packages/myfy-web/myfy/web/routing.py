"""
FastAPI-like routing with DI-powered handlers.

Routes are compiled at startup to build injection plans.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from inspect import signature
from typing import Any, get_type_hints

from myfy.core.config import BaseSettings


class HTTPMethod(str, Enum):
    """HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class Route:
    """
    Represents a registered route.

    Stores metadata needed for handler injection and execution.
    """

    path: str
    method: HTTPMethod
    handler: Callable
    name: str | None = None
    dependencies: list[str] = field(default_factory=list)
    path_params: list[str] = field(default_factory=list)
    body_param: str | None = None

    def __repr__(self) -> str:
        handler_name = getattr(self.handler, "__name__", "<lambda>")
        return f"Route({self.method.value} {self.path} -> {handler_name})"


class Router:
    """
    Route registry and decorator factory.

    Provides FastAPI-like decorator API:
        @route.get("/users/{user_id}")
        async def get_user(user_id: int, db: Database) -> User:
            ...
    """

    def __init__(self):
        self._routes: list[Route] = []

    def add_route(
        self,
        path: str,
        handler: Callable,
        method: HTTPMethod,
        name: str | None = None,
    ) -> Route:
        """
        Register a route.

        Args:
            path: URL path (may include {param} placeholders)
            handler: Handler function
            method: HTTP method
            name: Optional route name

        Returns:
            The created Route
        """
        route = Route(
            path=path,
            method=method,
            handler=handler,
            name=name or getattr(handler, "__name__", None),
        )

        # Parse path parameters
        route.path_params = self._extract_path_params(path)

        # Analyze handler signature for DI and params
        self._analyze_handler(route)

        self._routes.append(route)
        return route

    def get(self, path: str, name: str | None = None) -> Callable:
        """Decorator for GET routes."""
        return self._method_decorator(path, HTTPMethod.GET, name)

    def post(self, path: str, name: str | None = None) -> Callable:
        """Decorator for POST routes."""
        return self._method_decorator(path, HTTPMethod.POST, name)

    def put(self, path: str, name: str | None = None) -> Callable:
        """Decorator for PUT routes."""
        return self._method_decorator(path, HTTPMethod.PUT, name)

    def delete(self, path: str, name: str | None = None) -> Callable:
        """Decorator for DELETE routes."""
        return self._method_decorator(path, HTTPMethod.DELETE, name)

    def patch(self, path: str, name: str | None = None) -> Callable:
        """Decorator for PATCH routes."""
        return self._method_decorator(path, HTTPMethod.PATCH, name)

    def _method_decorator(self, path: str, method: HTTPMethod, name: str | None) -> Callable:
        """Generic decorator factory for HTTP methods."""

        def decorator(handler: Callable) -> Callable:
            self.add_route(path, handler, method, name)
            return handler

        return decorator

    def _extract_path_params(self, path: str) -> list[str]:
        """Extract parameter names from path template with validation."""
        params = []
        parts = path.split("/")
        param_pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

        for part in parts:
            if part.startswith("{") and part.endswith("}"):
                param_name = part[1:-1]

                # Validate parameter name is a valid Python identifier
                if not param_pattern.match(param_name):
                    raise ValueError(
                        f"Invalid path parameter name '{param_name}' in path '{path}'. "
                        "Must be a valid Python identifier."
                    )

                # Prevent duplicates
                if param_name in params:
                    raise ValueError(f"Duplicate path parameter '{param_name}' in path '{path}'")

                params.append(param_name)

        return params

    def _analyze_handler(self, route: Route) -> None:
        """
        Analyze handler signature to determine DI dependencies and parameters.

        Parameters are classified as:
        - Path parameters (from URL template)
        - Body parameter (annotated with a Pydantic model or dict)
        - DI dependencies (everything else - resolved from container)
        """
        sig = signature(route.handler)
        hints = get_type_hints(route.handler)

        for param_name in sig.parameters:
            # Skip if it's a path parameter
            if param_name in route.path_params:
                continue

            # Check if it's a body parameter (has type annotation that's not a builtin)
            param_type = hints.get(param_name)
            if param_type and self._is_body_type(param_type):
                route.body_param = param_name
            else:
                # It's a DI dependency
                route.dependencies.append(param_name)

    def _is_body_type(self, type_hint: Any) -> bool:
        """
        Determine if a type hint represents a request body.

        For now, we'll use a simple heuristic:
        - If it's a dict, list, or has a model_validate method (Pydantic), it's a body
        - EXCEPT if it's a Settings class (BaseSettings subclass) - those are DI dependencies
        - Otherwise, it's a DI dependency
        """
        # BaseSettings subclasses are always DI dependencies, never request bodies
        try:
            if isinstance(type_hint, type) and issubclass(type_hint, BaseSettings):
                return False
        except TypeError:
            pass

        if type_hint in (dict, list):
            return True
        # Check for Pydantic models
        if hasattr(type_hint, "model_validate"):
            return True
        # Check if it's a dataclass or similar
        return bool(hasattr(type_hint, "__dataclass_fields__"))

    def get_routes(self) -> list[Route]:
        """Get all registered routes."""
        return self._routes.copy()

    def __repr__(self) -> str:
        return f"Router(routes={len(self._routes)})"


# Global router instance (convenience)
route = Router()
