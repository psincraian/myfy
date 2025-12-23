"""
Convenience namespace for HTTP exceptions.

Provides short, readable aliases for common web errors.

Usage:
    from myfy.web import errors

    raise errors.NotFound("User not found")
    raise errors.BadRequest("Invalid email format", field="email")
    raise errors.Conflict("Username already taken")

For creating custom exceptions, import from myfy.web.exceptions:
    from myfy.web.exceptions import WebError

    class CustomError(WebError):
        status_code = 418
        error_type = "teapot"
"""

from .exceptions import (
    ConflictError as Conflict,
    ForbiddenError as Forbidden,
    NotFoundError as NotFound,
    RateLimitError as RateLimit,
    ServiceUnavailableError as ServiceUnavailable,
    UnauthorizedError as Unauthorized,
    UnprocessableEntityError as UnprocessableEntity,
    ValidationError as BadRequest,
    WebError as Base,
)

__all__ = [
    "Base",
    "BadRequest",
    "Unauthorized",
    "Forbidden",
    "NotFound",
    "Conflict",
    "UnprocessableEntity",
    "RateLimit",
    "ServiceUnavailable",
]
