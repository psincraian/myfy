"""
Request context management for web handlers.

Provides request-scoped context via contextvars.
"""

from contextvars import ContextVar
from typing import Any, Optional

from starlette.requests import Request

# Context variables for request-scoped data
_request_context: ContextVar[Optional["RequestContext"]] = ContextVar[Optional["RequestContext"]](
    "_request_context", default=None
)


class RequestContext:
    """
    Container for request-scoped data.

    Available to handlers via dependency injection.
    Automatically populated by the ASGI adapter.
    """

    def __init__(self, request: Request):
        self.request = request
        self._data: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the context."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the context."""
        self._data[key] = value

    @property
    def method(self) -> str:
        """HTTP method."""
        return self.request.method

    @property
    def url(self) -> str:
        """Request URL."""
        return str(self.request.url)

    @property
    def path(self) -> str:
        """Request path."""
        return self.request.url.path

    @property
    def headers(self) -> dict[str, str]:
        """Request headers."""
        return dict(self.request.headers)

    async def json(self) -> Any:
        """Parse request body as JSON."""
        return await self.request.json()

    async def body(self) -> bytes:
        """Get raw request body."""
        return await self.request.body()

    def __repr__(self) -> str:
        return f"RequestContext({self.method} {self.path})"


def get_request_context() -> RequestContext | None:
    """Get the current request context (if in a request scope)."""
    return _request_context.get()


def set_request_context(context: RequestContext) -> None:
    """Set the request context (called by ASGI adapter)."""
    _request_context.set(context)


def clear_request_context() -> None:
    """Clear the request context (called after request completes)."""
    _request_context.set(None)
