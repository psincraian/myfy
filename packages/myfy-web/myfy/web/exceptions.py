"""
Web exceptions for myfy framework.

Provides a hierarchy of exceptions that automatically map to HTTP responses.
All exceptions follow RFC 7807 Problem Details format.

Usage:
    from myfy.web.exceptions import WebError, NotFoundError

    # Use built-in exceptions
    raise NotFoundError("User not found")

    # Create custom exceptions
    class PaymentRequiredError(WebError):
        status_code = 402
        error_type = "payment_required"

    raise PaymentRequiredError("Insufficient credits", required=100)
"""

from typing import Any


class WebError(Exception):
    """Base exception for errors that map to HTTP responses.

    Subclass this to create domain-specific errors that the framework
    automatically converts to appropriate HTTP responses.

    The exception follows RFC 7807 Problem Details format, which provides
    a standard way to communicate error information in HTTP APIs.

    Attributes:
        status_code: HTTP status code (default: 500)
        error_type: Error type URI for RFC 7807 Problem Details (default: "about:blank")

    Example:
        class UserNotFoundError(WebError):
            status_code = 404
            error_type = "user_not_found"

        raise UserNotFoundError(f"User {user_id} not found")
    """

    status_code: int = 500
    error_type: str = "about:blank"

    def __init__(self, message: str, **extra: Any):
        """Initialize the exception.

        Args:
            message: Human-readable error description
            **extra: Additional fields to include in Problem Details response
        """
        super().__init__(message)
        self.extra = extra

    def to_problem_detail(self) -> dict[str, Any]:
        """Convert to RFC 7807 Problem Details format.

        Returns:
            Dictionary with standard Problem Details fields plus any extra fields.

        Example:
            >>> error = NotFoundError("User not found", user_id=123)
            >>> error.to_problem_detail()
            {
                "type": "not_found",
                "title": "NotFoundError",
                "status": 404,
                "detail": "User not found",
                "user_id": 123
            }
        """
        return {
            "type": self.error_type,
            "title": type(self).__name__,
            "status": self.status_code,
            "detail": str(self),
            **self.extra,
        }


class ValidationError(WebError):
    """Raised when request validation fails.

    Use for invalid input, malformed requests, or constraint violations.

    Example:
        raise ValidationError("Invalid email format", field="email")
    """

    status_code = 400
    error_type = "validation_error"


class UnauthorizedError(WebError):
    """Raised when authentication is required but missing or invalid.

    Use when the request lacks valid authentication credentials.

    Example:
        raise UnauthorizedError("Invalid or expired token")
    """

    status_code = 401
    error_type = "unauthorized"


class ForbiddenError(WebError):
    """Raised when the authenticated user lacks permission.

    Use when the user is authenticated but not authorized for the action.

    Example:
        raise ForbiddenError("You don't have permission to delete this resource")
    """

    status_code = 403
    error_type = "forbidden"


class NotFoundError(WebError):
    """Raised when a requested resource does not exist.

    Use when a specific entity cannot be found by its identifier.

    Example:
        raise NotFoundError(f"Project '{project_name}' not found")
    """

    status_code = 404
    error_type = "not_found"


class ConflictError(WebError):
    """Raised when the request conflicts with current state.

    Use for duplicate entries, version conflicts, or state violations.

    Example:
        raise ConflictError("Username already taken", username="john_doe")
    """

    status_code = 409
    error_type = "conflict"


class UnprocessableEntityError(WebError):
    """Raised when the request is well-formed but semantically invalid.

    Use when the request syntax is correct but the content cannot be processed.

    Example:
        raise UnprocessableEntityError("Cannot assign task to inactive user")
    """

    status_code = 422
    error_type = "unprocessable_entity"


class RateLimitError(WebError):
    """Raised when rate limit is exceeded.

    Use to signal that the client should slow down requests.

    Example:
        raise RateLimitError("Too many requests", retry_after=60)
    """

    status_code = 429
    error_type = "rate_limit_exceeded"


class ServiceUnavailableError(WebError):
    """Raised when a required service is temporarily unavailable.

    Use for temporary outages, maintenance, or upstream failures.

    Example:
        raise ServiceUnavailableError("Database temporarily unavailable")
    """

    status_code = 503
    error_type = "service_unavailable"
