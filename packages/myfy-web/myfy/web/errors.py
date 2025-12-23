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

from .exceptions import ConflictError as Conflict
from .exceptions import ForbiddenError as Forbidden
from .exceptions import NotFoundError as NotFound
from .exceptions import RateLimitError as RateLimit
from .exceptions import ServiceUnavailableError as ServiceUnavailable
from .exceptions import UnauthorizedError as Unauthorized
from .exceptions import UnprocessableEntityError as UnprocessableEntity
from .exceptions import ValidationError as BadRequest
from .exceptions import WebError as Base

__all__ = [
    "BadRequest",
    "Base",
    "Conflict",
    "Forbidden",
    "NotFound",
    "RateLimit",
    "ServiceUnavailable",
    "Unauthorized",
    "UnprocessableEntity",
]
