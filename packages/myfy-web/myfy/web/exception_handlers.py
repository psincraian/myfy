"""
Centralized exception handler registry for the web module.

This module provides a way to register exception handlers that automatically
convert domain exceptions to HTTP responses. It eliminates the need for
repetitive try/except blocks in route handlers.

Usage:
    from myfy.web import exception_handlers

    # Register a custom exception handler
    @exception_handlers.handler(MyCustomException)
    async def handle_custom_exception(request, exc):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "code": "CUSTOM_ERROR"}
        )

    # Or register programmatically
    exception_handlers.register(MyException, my_handler_function)

The registry comes with default handlers for:
- HTTPMappedException and all subclasses (ValidationException, NotFoundException, etc.)
- ValueError -> 400 Bad Request
- PermissionError -> 403 Forbidden
- LookupError (KeyError, IndexError) -> 404 Not Found
"""

from collections.abc import Awaitable, Callable
from typing import TypeVar

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .exceptions import HTTPMappedException

# Type for exception handlers
ExcType = TypeVar("ExcType", bound=Exception)
ExceptionHandler = Callable[[Request, Exception], Response | Awaitable[Response]]


class ExceptionHandlerRegistry:
    """
    Registry for exception handlers.

    Maps exception types to handler functions that convert them to HTTP responses.
    Supports inheritance - if no exact match is found, parent classes are checked.
    """

    def __init__(self) -> None:
        """Initialize the registry with default handlers."""
        self._handlers: dict[type[Exception], ExceptionHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default handlers for common exceptions."""
        # HTTPMappedException and subclasses
        self.register(HTTPMappedException, self._handle_http_mapped_exception)

        # Python built-in exceptions with sensible HTTP mappings
        self.register(ValueError, self._handle_value_error)
        self.register(TypeError, self._handle_type_error)
        self.register(PermissionError, self._handle_permission_error)
        self.register(LookupError, self._handle_lookup_error)  # KeyError, IndexError
        self.register(NotImplementedError, self._handle_not_implemented)

    def register(
        self,
        exc_class: type[Exception],
        handler: ExceptionHandler,
    ) -> None:
        """
        Register an exception handler.

        Args:
            exc_class: The exception class to handle
            handler: Function that takes (request, exception) and returns a Response
        """
        self._handlers[exc_class] = handler

    def handler(
        self, exc_class: type[ExcType]
    ) -> Callable[[ExceptionHandler], ExceptionHandler]:
        """
        Decorator to register an exception handler.

        Usage:
            @exception_handlers.handler(MyException)
            async def handle_my_exception(request, exc):
                return JSONResponse(status_code=400, content={"error": str(exc)})
        """

        def decorator(func: ExceptionHandler) -> ExceptionHandler:
            self.register(exc_class, func)
            return func

        return decorator

    def get_handler(self, exc: Exception) -> ExceptionHandler | None:
        """
        Get the handler for an exception.

        Checks exact type first, then walks up the MRO to find a matching handler.

        Args:
            exc: The exception instance

        Returns:
            The handler function if found, None otherwise
        """
        exc_type = type(exc)

        # Check exact match first
        if exc_type in self._handlers:
            return self._handlers[exc_type]

        # Walk up the MRO to find a handler
        for base_type in exc_type.__mro__[1:]:
            if base_type in self._handlers:
                return self._handlers[base_type]

        return None

    async def handle(self, request: Request, exc: Exception) -> Response | None:
        """
        Handle an exception by looking up and calling the appropriate handler.

        Args:
            request: The Starlette request
            exc: The exception to handle

        Returns:
            Response if a handler was found and executed, None otherwise
        """
        handler = self.get_handler(exc)
        if handler is None:
            return None

        result = handler(request, exc)
        # Handle both sync and async handlers
        if hasattr(result, "__await__"):
            return await result
        return result  # type: ignore[return-value]

    def can_handle(self, exc: Exception) -> bool:
        """Check if this registry can handle the given exception."""
        return self.get_handler(exc) is not None

    # =========================================================================
    # Default handlers
    # =========================================================================

    @staticmethod
    def _handle_http_mapped_exception(
        request: Request, exc: HTTPMappedException
    ) -> JSONResponse:
        """Handle HTTPMappedException and subclasses."""
        return JSONResponse(
            content={"detail": exc.detail},
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @staticmethod
    def _handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
        """Handle ValueError - maps to 400 Bad Request."""
        return JSONResponse(
            content={"detail": str(exc)},
            status_code=400,
        )

    @staticmethod
    def _handle_type_error(request: Request, exc: TypeError) -> JSONResponse:
        """Handle TypeError - maps to 400 Bad Request."""
        return JSONResponse(
            content={"detail": str(exc)},
            status_code=400,
        )

    @staticmethod
    def _handle_permission_error(
        request: Request, exc: PermissionError
    ) -> JSONResponse:
        """Handle PermissionError - maps to 403 Forbidden."""
        return JSONResponse(
            content={"detail": str(exc) or "Permission denied"},
            status_code=403,
        )

    @staticmethod
    def _handle_lookup_error(request: Request, exc: LookupError) -> JSONResponse:
        """Handle LookupError (KeyError, IndexError) - maps to 404 Not Found."""
        return JSONResponse(
            content={"detail": str(exc) or "Resource not found"},
            status_code=404,
        )

    @staticmethod
    def _handle_not_implemented(
        request: Request, exc: NotImplementedError
    ) -> JSONResponse:
        """Handle NotImplementedError - maps to 501 Not Implemented."""
        return JSONResponse(
            content={"detail": str(exc) or "Not implemented"},
            status_code=501,
        )


# Global registry instance
exception_handlers = ExceptionHandlerRegistry()
