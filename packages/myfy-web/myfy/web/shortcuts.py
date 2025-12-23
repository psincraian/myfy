"""
Flask-style convenience functions for raising HTTP exceptions.

Provides a simple abort() function for quick error responses.

Usage:
    from myfy.web import abort

    # Basic usage
    abort(404, "User not found")

    # With extra fields
    abort(400, "Invalid email format", field="email")

    # Just status code
    abort(403)  # Uses default message
"""

from typing import NoReturn

from .exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    UnauthorizedError,
    UnprocessableEntityError,
    ValidationError,
    WebError,
)

# Mapping from status codes to exception classes
_STATUS_CODE_MAP: dict[int, type[WebError]] = {
    400: ValidationError,
    401: UnauthorizedError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    422: UnprocessableEntityError,
    429: RateLimitError,
    503: ServiceUnavailableError,
}

# Default messages for status codes
_DEFAULT_MESSAGES: dict[int, str] = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    503: "Service Unavailable",
}


def abort(status_code: int, message: str | None = None, **extra) -> NoReturn:
    """Raise an HTTP exception by status code.

    A convenient way to raise HTTP errors without importing specific exception classes.
    Inspired by Flask's abort() function.

    Args:
        status_code: HTTP status code (400, 401, 403, 404, 409, 422, 429, 500, 503)
        message: Error message. If not provided, uses a default message.
        **extra: Additional fields to include in the Problem Details response.

    Raises:
        WebError: A subclass matching the status code, or base WebError for unknown codes.

    Example:
        # Simple usage
        abort(404, "User not found")

        # With extra context
        abort(400, "Invalid value", field="email", provided="not-an-email")

        # Using default message
        abort(403)  # Raises ForbiddenError with message "Forbidden"

        # Unknown status code falls back to WebError
        abort(418, "I'm a teapot")  # WebError with status_code=418
    """
    # Get default message if none provided
    if message is None:
        message = _DEFAULT_MESSAGES.get(status_code, "An error occurred")

    # Get the appropriate exception class
    exc_class = _STATUS_CODE_MAP.get(status_code, WebError)

    # Create and raise the exception
    exc = exc_class(message, **extra)

    # Override status code if using base WebError for unmapped codes
    if exc_class is WebError and status_code != 500:
        exc.status_code = status_code

    raise exc
