"""
Integration tests for centralized exception handling.

These tests verify:
- Domain exceptions map to correct HTTP status codes
- Exception handler registry correctly dispatches exceptions
- Custom exception handlers can be registered
- Handler inheritance works correctly
- Integration with HandlerExecutor
"""

import json
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from myfy.core.config import CoreSettings
from myfy.core.di import SINGLETON, Container
from myfy.web.exception_handlers import ExceptionHandlerRegistry, exception_handlers
from myfy.web.exceptions import (
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
from myfy.web.handlers import HandlerExecutor
from myfy.web.routing import HTTPMethod, Route

pytestmark = pytest.mark.integration


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_request() -> MagicMock:
    """Create a mock Starlette request."""
    request = MagicMock(spec=Request)
    request.path_params = {}
    request.method = "GET"
    return request


@pytest.fixture
def fresh_registry() -> ExceptionHandlerRegistry:
    """Create a fresh exception handler registry for testing."""
    return ExceptionHandlerRegistry()


@pytest.fixture
def service_container() -> Container:
    """Container with test services registered."""
    container = Container()
    container.register(
        type_=CoreSettings,
        factory=lambda: CoreSettings(debug=False),
        scope=SINGLETON,
    )
    container.compile()
    return container


def make_mock_request(
    path_params: dict | None = None,
    body: bytes | None = None,
    method: str = "GET",
) -> MagicMock:
    """Create a mock Starlette request."""
    request = MagicMock(spec=Request)
    request.path_params = path_params or {}
    request.method = method

    async def get_body():
        return body or b""

    async def get_json():
        return json.loads(body.decode()) if body else {}

    request.body = get_body
    request.json = get_json

    return request


# =============================================================================
# Domain Exception Tests
# =============================================================================


class TestDomainExceptions:
    """Test domain exception classes."""

    def test_validation_exception_defaults(self):
        """Test ValidationException has correct defaults."""
        exc = ValidationException()
        assert exc.status_code == 400
        assert exc.detail == "Validation failed"
        assert exc.headers is None

    def test_validation_exception_custom_detail(self):
        """Test ValidationException with custom detail."""
        exc = ValidationException("Email format is invalid")
        assert exc.status_code == 400
        assert exc.detail == "Email format is invalid"

    def test_not_found_exception_defaults(self):
        """Test NotFoundException has correct defaults."""
        exc = NotFoundException()
        assert exc.status_code == 404
        assert exc.detail == "Resource not found"

    def test_not_found_exception_with_resource_info(self):
        """Test NotFoundException with resource type and ID."""
        exc = NotFoundException(resource_type="User", resource_id=123)
        assert exc.status_code == 404
        assert exc.detail == "User '123' not found"
        assert exc.resource_type == "User"
        assert exc.resource_id == 123

    def test_not_found_exception_resource_type_only(self):
        """Test NotFoundException with resource type only."""
        exc = NotFoundException(resource_type="Project")
        assert exc.detail == "Project not found"

    def test_unauthorized_exception_defaults(self):
        """Test UnauthorizedException has correct defaults."""
        exc = UnauthorizedException()
        assert exc.status_code == 401
        assert exc.detail == "Authentication required"

    def test_unauthorized_exception_with_www_authenticate(self):
        """Test UnauthorizedException with WWW-Authenticate header."""
        exc = UnauthorizedException(www_authenticate="Bearer")
        assert exc.status_code == 401
        assert exc.headers == {"WWW-Authenticate": "Bearer"}

    def test_forbidden_exception_defaults(self):
        """Test ForbiddenException has correct defaults."""
        exc = ForbiddenException()
        assert exc.status_code == 403
        assert exc.detail == "Access forbidden"

    def test_conflict_exception_defaults(self):
        """Test ConflictException has correct defaults."""
        exc = ConflictException()
        assert exc.status_code == 409
        assert exc.detail == "Resource conflict"

    def test_gone_exception_defaults(self):
        """Test GoneException has correct defaults."""
        exc = GoneException()
        assert exc.status_code == 410
        assert exc.detail == "Resource no longer available"

    def test_unprocessable_entity_exception_defaults(self):
        """Test UnprocessableEntityException has correct defaults."""
        exc = UnprocessableEntityException()
        assert exc.status_code == 422
        assert exc.detail == "Unprocessable entity"

    def test_too_many_requests_exception_with_retry_after(self):
        """Test TooManyRequestsException with Retry-After header."""
        exc = TooManyRequestsException(retry_after=60)
        assert exc.status_code == 429
        assert exc.headers == {"Retry-After": "60"}

    def test_service_unavailable_exception_with_retry_after(self):
        """Test ServiceUnavailableException with Retry-After header."""
        exc = ServiceUnavailableException(retry_after=300)
        assert exc.status_code == 503
        assert exc.headers == {"Retry-After": "300"}

    def test_exception_repr(self):
        """Test exception string representation."""
        exc = NotFoundException("User not found")
        assert "NotFoundException" in repr(exc)
        assert "404" in repr(exc)
        assert "User not found" in repr(exc)


# =============================================================================
# Exception Handler Registry Tests
# =============================================================================


class TestExceptionHandlerRegistry:
    """Test the exception handler registry."""

    @pytest.mark.asyncio
    async def test_handle_http_mapped_exception(
        self, fresh_registry: ExceptionHandlerRegistry, mock_request: MagicMock
    ):
        """Test handling HTTPMappedException."""
        exc = NotFoundException("User not found")
        response = await fresh_registry.handle(mock_request, exc)

        assert response is not None
        assert response.status_code == 404
        body = json.loads(response.body.decode())
        assert body["detail"] == "User not found"

    @pytest.mark.asyncio
    async def test_handle_value_error(
        self, fresh_registry: ExceptionHandlerRegistry, mock_request: MagicMock
    ):
        """Test handling ValueError."""
        exc = ValueError("Invalid value")
        response = await fresh_registry.handle(mock_request, exc)

        assert response is not None
        assert response.status_code == 400
        body = json.loads(response.body.decode())
        assert body["detail"] == "Invalid value"

    @pytest.mark.asyncio
    async def test_handle_permission_error(
        self, fresh_registry: ExceptionHandlerRegistry, mock_request: MagicMock
    ):
        """Test handling PermissionError."""
        exc = PermissionError("Access denied")
        response = await fresh_registry.handle(mock_request, exc)

        assert response is not None
        assert response.status_code == 403
        body = json.loads(response.body.decode())
        assert body["detail"] == "Access denied"

    @pytest.mark.asyncio
    async def test_handle_key_error(
        self, fresh_registry: ExceptionHandlerRegistry, mock_request: MagicMock
    ):
        """Test handling KeyError (subclass of LookupError)."""
        exc = KeyError("missing_key")
        response = await fresh_registry.handle(mock_request, exc)

        assert response is not None
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_handle_not_implemented_error(
        self, fresh_registry: ExceptionHandlerRegistry, mock_request: MagicMock
    ):
        """Test handling NotImplementedError."""
        exc = NotImplementedError("Feature not implemented")
        response = await fresh_registry.handle(mock_request, exc)

        assert response is not None
        assert response.status_code == 501

    @pytest.mark.asyncio
    async def test_unregistered_exception_returns_none(
        self, fresh_registry: ExceptionHandlerRegistry, mock_request: MagicMock
    ):
        """Test that unregistered exception returns None."""

        class CustomException(Exception):
            pass

        exc = CustomException("Custom error")
        response = await fresh_registry.handle(mock_request, exc)

        assert response is None

    def test_can_handle_registered_exception(
        self, fresh_registry: ExceptionHandlerRegistry
    ):
        """Test can_handle returns True for registered exceptions."""
        assert fresh_registry.can_handle(ValueError("test"))
        assert fresh_registry.can_handle(NotFoundException("test"))

    def test_can_handle_unregistered_exception(
        self, fresh_registry: ExceptionHandlerRegistry
    ):
        """Test can_handle returns False for unregistered exceptions."""

        class UnknownException(Exception):
            pass

        assert not fresh_registry.can_handle(UnknownException())

    @pytest.mark.asyncio
    async def test_register_custom_handler(
        self, fresh_registry: ExceptionHandlerRegistry, mock_request: MagicMock
    ):
        """Test registering a custom exception handler."""

        class MyCustomException(Exception):
            pass

        def custom_handler(request, exc):
            return JSONResponse(
                status_code=418,
                content={"error": "I'm a teapot", "message": str(exc)},
            )

        fresh_registry.register(MyCustomException, custom_handler)

        exc = MyCustomException("Custom error")
        response = await fresh_registry.handle(mock_request, exc)

        assert response is not None
        assert response.status_code == 418
        body = json.loads(response.body.decode())
        assert body["error"] == "I'm a teapot"

    @pytest.mark.asyncio
    async def test_decorator_registration(
        self, fresh_registry: ExceptionHandlerRegistry, mock_request: MagicMock
    ):
        """Test registering handler via decorator."""

        class DecoratorException(Exception):
            pass

        @fresh_registry.handler(DecoratorException)
        def handle_decorator_exception(request, exc):
            return JSONResponse(status_code=499, content={"handled": True})

        exc = DecoratorException()
        response = await fresh_registry.handle(mock_request, exc)

        assert response is not None
        assert response.status_code == 499

    @pytest.mark.asyncio
    async def test_inheritance_handling(
        self, fresh_registry: ExceptionHandlerRegistry, mock_request: MagicMock
    ):
        """Test that exception inheritance is respected."""

        class BaseCustomException(Exception):
            pass

        class DerivedCustomException(BaseCustomException):
            pass

        def base_handler(request, exc):
            return JSONResponse(status_code=450, content={"type": "base"})

        fresh_registry.register(BaseCustomException, base_handler)

        # Derived exception should be handled by base handler
        exc = DerivedCustomException("Derived error")
        response = await fresh_registry.handle(mock_request, exc)

        assert response is not None
        assert response.status_code == 450

    @pytest.mark.asyncio
    async def test_exact_match_preferred_over_inheritance(
        self, fresh_registry: ExceptionHandlerRegistry, mock_request: MagicMock
    ):
        """Test that exact type match is preferred over parent handler."""

        class BaseException(Exception):
            pass

        class DerivedException(BaseException):
            pass

        def base_handler(request, exc):
            return JSONResponse(status_code=450, content={"type": "base"})

        def derived_handler(request, exc):
            return JSONResponse(status_code=451, content={"type": "derived"})

        fresh_registry.register(BaseException, base_handler)
        fresh_registry.register(DerivedException, derived_handler)

        # Derived exception should use derived handler
        exc = DerivedException()
        response = await fresh_registry.handle(mock_request, exc)

        assert response is not None
        assert response.status_code == 451

    @pytest.mark.asyncio
    async def test_async_handler(
        self, fresh_registry: ExceptionHandlerRegistry, mock_request: MagicMock
    ):
        """Test async exception handlers work correctly."""

        class AsyncException(Exception):
            pass

        async def async_handler(request, exc):
            return JSONResponse(status_code=452, content={"async": True})

        fresh_registry.register(AsyncException, async_handler)

        exc = AsyncException()
        response = await fresh_registry.handle(mock_request, exc)

        assert response is not None
        assert response.status_code == 452

    @pytest.mark.asyncio
    async def test_headers_preserved(
        self, fresh_registry: ExceptionHandlerRegistry, mock_request: MagicMock
    ):
        """Test that exception headers are preserved in response."""
        exc = UnauthorizedException(www_authenticate="Bearer realm='api'")
        response = await fresh_registry.handle(mock_request, exc)

        assert response is not None
        assert response.headers.get("WWW-Authenticate") == "Bearer realm='api'"


# =============================================================================
# HandlerExecutor Integration Tests
# =============================================================================


class TestHandlerExecutorExceptionIntegration:
    """Test exception handling integration with HandlerExecutor."""

    @pytest.mark.asyncio
    async def test_value_error_returns_400(self, service_container: Container):
        """Test ValueError is handled and returns 400."""
        executor = HandlerExecutor(service_container)

        async def handler():
            raise ValueError("Invalid input")

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 400
        body = json.loads(response.body.decode())
        assert body["detail"] == "Invalid input"

    @pytest.mark.asyncio
    async def test_not_found_exception_returns_404(self, service_container: Container):
        """Test NotFoundException is handled and returns 404."""
        executor = HandlerExecutor(service_container)

        async def handler():
            raise NotFoundException(resource_type="User", resource_id=123)

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 404
        body = json.loads(response.body.decode())
        assert "User '123' not found" in body["detail"]

    @pytest.mark.asyncio
    async def test_validation_exception_returns_400(self, service_container: Container):
        """Test ValidationException is handled and returns 400."""
        executor = HandlerExecutor(service_container)

        async def handler():
            raise ValidationException("Email format is invalid")

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 400
        body = json.loads(response.body.decode())
        assert body["detail"] == "Email format is invalid"

    @pytest.mark.asyncio
    async def test_unauthorized_exception_returns_401(
        self, service_container: Container
    ):
        """Test UnauthorizedException is handled and returns 401."""
        executor = HandlerExecutor(service_container)

        async def handler():
            raise UnauthorizedException(www_authenticate="Bearer")

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 401
        assert response.headers.get("WWW-Authenticate") == "Bearer"

    @pytest.mark.asyncio
    async def test_forbidden_exception_returns_403(self, service_container: Container):
        """Test ForbiddenException is handled and returns 403."""
        executor = HandlerExecutor(service_container)

        async def handler():
            raise ForbiddenException("You don't have permission")

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 403
        body = json.loads(response.body.decode())
        assert body["detail"] == "You don't have permission"

    @pytest.mark.asyncio
    async def test_conflict_exception_returns_409(self, service_container: Container):
        """Test ConflictException is handled and returns 409."""
        executor = HandlerExecutor(service_container)

        async def handler():
            raise ConflictException("Resource already exists")

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 409
        body = json.loads(response.body.decode())
        assert body["detail"] == "Resource already exists"

    @pytest.mark.asyncio
    async def test_permission_error_returns_403(self, service_container: Container):
        """Test Python PermissionError is handled and returns 403."""
        executor = HandlerExecutor(service_container)

        async def handler():
            raise PermissionError("Access denied")

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_key_error_returns_404(self, service_container: Container):
        """Test KeyError (LookupError) is handled and returns 404."""
        executor = HandlerExecutor(service_container)

        async def handler():
            raise KeyError("item_not_found")

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_custom_registry_used(self, service_container: Container):
        """Test that a custom exception registry can be provided."""
        custom_registry = ExceptionHandlerRegistry()

        class SpecialException(Exception):
            pass

        custom_registry.register(
            SpecialException,
            lambda req, exc: JSONResponse(
                status_code=499, content={"special": True}
            ),
        )

        executor = HandlerExecutor(service_container, exception_registry=custom_registry)

        async def handler():
            raise SpecialException("Special error")

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 499
        body = json.loads(response.body.decode())
        assert body["special"] is True

    @pytest.mark.asyncio
    async def test_unhandled_exception_falls_back_to_500(
        self, service_container: Container
    ):
        """Test unhandled exceptions fall back to 500 error."""
        # Create a custom registry without RuntimeError handler
        custom_registry = ExceptionHandlerRegistry()
        # Clear all default handlers
        custom_registry._handlers.clear()

        executor = HandlerExecutor(service_container, exception_registry=custom_registry)

        async def handler():
            raise RuntimeError("Unhandled error")

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 500


# =============================================================================
# Global Registry Tests
# =============================================================================


class TestGlobalExceptionHandlers:
    """Test the global exception_handlers instance."""

    def test_global_registry_exists(self):
        """Test that global exception_handlers is available."""
        assert exception_handlers is not None
        assert isinstance(exception_handlers, ExceptionHandlerRegistry)

    def test_global_registry_has_default_handlers(self):
        """Test that global registry has default handlers registered."""
        assert exception_handlers.can_handle(ValueError("test"))
        assert exception_handlers.can_handle(NotFoundException("test"))
        assert exception_handlers.can_handle(ValidationException("test"))
        assert exception_handlers.can_handle(PermissionError("test"))
