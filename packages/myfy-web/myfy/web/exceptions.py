"""
HTTP-mappable domain exceptions for the web module.

This module provides a hierarchy of exceptions that automatically map to
HTTP status codes. Route handlers can raise these exceptions, and they
will be automatically converted to appropriate HTTP responses by the
exception handler registry.

Usage:
    from myfy.web.exceptions import NotFoundException, ValidationException

    @route.get("/users/{user_id}")
    async def get_user(user_id: int, db: Database) -> User:
        user = await db.get_user(user_id)
        if not user:
            raise NotFoundException(f"User {user_id} not found")
        return user

    @route.post("/users")
    async def create_user(body: CreateUserRequest, db: Database) -> User:
        if not is_valid_email(body.email):
            raise ValidationException("Invalid email format")
        return await db.create_user(body)
"""

from typing import Any


class HTTPMappedException(Exception):
    """
    Base class for exceptions that map to HTTP status codes.

    Subclasses define the status_code and can provide additional
    details that will be included in the HTTP response.

    Attributes:
        status_code: HTTP status code to return
        detail: Human-readable error message
        headers: Optional headers to include in the response
    """

    status_code: int = 500
    default_detail: str = "An error occurred"

    def __init__(
        self,
        detail: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """
        Initialize the exception.

        Args:
            detail: Human-readable error message. If not provided,
                   uses the class default_detail.
            headers: Optional headers to include in the HTTP response.
        """
        self.detail = detail or self.default_detail
        self.headers = headers
        super().__init__(self.detail)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(status_code={self.status_code}, detail={self.detail!r})"


class ValidationException(HTTPMappedException):
    """
    Raised when request validation fails.

    Maps to HTTP 400 Bad Request.

    Examples:
        - Invalid parameter format
        - Missing required fields
        - Value out of allowed range
        - Business rule validation failure
    """

    status_code = 400
    default_detail = "Validation failed"


class UnauthorizedException(HTTPMappedException):
    """
    Raised when authentication is required but not provided or invalid.

    Maps to HTTP 401 Unauthorized.

    Examples:
        - Missing authentication token
        - Expired token
        - Invalid credentials
    """

    status_code = 401
    default_detail = "Authentication required"

    def __init__(
        self,
        detail: str | None = None,
        headers: dict[str, str] | None = None,
        *,
        www_authenticate: str | None = None,
    ) -> None:
        """
        Initialize the exception.

        Args:
            detail: Human-readable error message.
            headers: Optional headers to include in the HTTP response.
            www_authenticate: Value for WWW-Authenticate header.
        """
        if www_authenticate:
            headers = headers or {}
            headers["WWW-Authenticate"] = www_authenticate
        super().__init__(detail, headers)


class ForbiddenException(HTTPMappedException):
    """
    Raised when the user is authenticated but lacks permission.

    Maps to HTTP 403 Forbidden.

    Examples:
        - User trying to access another user's data
        - Insufficient role/permissions
        - Resource access denied
    """

    status_code = 403
    default_detail = "Access forbidden"


class NotFoundException(HTTPMappedException):
    """
    Raised when a requested resource cannot be found.

    Maps to HTTP 404 Not Found.

    Examples:
        - Entity with given ID doesn't exist
        - Route exists but resource is missing
        - Soft-deleted resource
    """

    status_code = 404
    default_detail = "Resource not found"

    def __init__(
        self,
        detail: str | None = None,
        headers: dict[str, str] | None = None,
        *,
        resource_type: str | None = None,
        resource_id: Any | None = None,
    ) -> None:
        """
        Initialize the exception.

        Args:
            detail: Human-readable error message.
            headers: Optional headers to include in the HTTP response.
            resource_type: Type of resource that was not found (e.g., "User", "Project").
            resource_id: ID of the resource that was not found.
        """
        if detail is None and resource_type:
            if resource_id is not None:
                detail = f"{resource_type} '{resource_id}' not found"
            else:
                detail = f"{resource_type} not found"
        super().__init__(detail, headers)
        self.resource_type = resource_type
        self.resource_id = resource_id


class ConflictException(HTTPMappedException):
    """
    Raised when there's a conflict with the current state of the resource.

    Maps to HTTP 409 Conflict.

    Examples:
        - Duplicate unique constraint violation
        - Optimistic locking conflict
        - State transition not allowed
    """

    status_code = 409
    default_detail = "Resource conflict"


class GoneException(HTTPMappedException):
    """
    Raised when a resource has been permanently deleted.

    Maps to HTTP 410 Gone.

    Examples:
        - Permanently deleted resource
        - Deprecated endpoint
    """

    status_code = 410
    default_detail = "Resource no longer available"


class UnprocessableEntityException(HTTPMappedException):
    """
    Raised when the request is syntactically correct but semantically invalid.

    Maps to HTTP 422 Unprocessable Entity.

    Examples:
        - Business logic validation failures
        - Invalid entity state for operation
    """

    status_code = 422
    default_detail = "Unprocessable entity"


class TooManyRequestsException(HTTPMappedException):
    """
    Raised when rate limits are exceeded.

    Maps to HTTP 429 Too Many Requests.

    Examples:
        - API rate limit exceeded
        - Too many login attempts
    """

    status_code = 429
    default_detail = "Too many requests"

    def __init__(
        self,
        detail: str | None = None,
        headers: dict[str, str] | None = None,
        *,
        retry_after: int | None = None,
    ) -> None:
        """
        Initialize the exception.

        Args:
            detail: Human-readable error message.
            headers: Optional headers to include in the HTTP response.
            retry_after: Seconds until the client can retry.
        """
        if retry_after is not None:
            headers = headers or {}
            headers["Retry-After"] = str(retry_after)
        super().__init__(detail, headers)


class ServiceUnavailableException(HTTPMappedException):
    """
    Raised when a service is temporarily unavailable.

    Maps to HTTP 503 Service Unavailable.

    Examples:
        - Database connection failure
        - External service down
        - Maintenance mode
    """

    status_code = 503
    default_detail = "Service temporarily unavailable"

    def __init__(
        self,
        detail: str | None = None,
        headers: dict[str, str] | None = None,
        *,
        retry_after: int | None = None,
    ) -> None:
        """
        Initialize the exception.

        Args:
            detail: Human-readable error message.
            headers: Optional headers to include in the HTTP response.
            retry_after: Seconds until the service may be available again.
        """
        if retry_after is not None:
            headers = headers or {}
            headers["Retry-After"] = str(retry_after)
        super().__init__(detail, headers)
