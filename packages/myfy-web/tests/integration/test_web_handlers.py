"""
Integration tests for myfy-web handler execution.

These tests verify:
- Handler compilation and execution
- Path parameter conversion
- Request body parsing
- Response generation
- Error handling
"""

import json
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from myfy.core.config import CoreSettings
from myfy.core.di import SINGLETON, Container
from myfy.web.handlers import HandlerExecutor
from myfy.web.routing import HTTPMethod, Route

pytestmark = pytest.mark.integration


# =============================================================================
# Test Models
# =============================================================================


class CreateUserRequest(BaseModel):
    """Pydantic model for user creation."""

    name: str
    email: str


@dataclass
class UserDataclass:
    """Dataclass for user data."""

    id: int
    name: str


class UserService:
    """Mock service for testing DI."""

    def get_user(self, user_id: int) -> dict:
        return {"id": user_id, "name": f"User {user_id}"}


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def service_container() -> Container:
    """Container with test services registered."""
    container = Container()
    container.register(
        type_=UserService,
        factory=lambda: UserService(),
        scope=SINGLETON,
    )
    container.register(
        type_=CoreSettings,
        factory=lambda: CoreSettings(debug=False),
        scope=SINGLETON,
    )
    container.compile()
    return container


@pytest.fixture
def debug_container() -> Container:
    """Container with debug mode enabled."""
    container = Container()
    container.register(
        type_=CoreSettings,
        factory=lambda: CoreSettings(debug=True),
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
# Handler Compilation Tests
# =============================================================================


class TestHandlerCompilation:
    """Test handler compilation functionality."""

    def test_compile_simple_route(self, service_container: Container):
        """Test compiling a simple route."""
        executor = HandlerExecutor(service_container)

        async def handler():
            return {"status": "ok"}

        route = Route(
            path="/health",
            method=HTTPMethod.GET,
            handler=handler,
            name="health",
        )

        # Should not raise
        executor.compile_route(route)
        assert executor._route_key(route) in executor._execution_plans

    def test_compile_route_with_dependencies(self, service_container: Container):
        """Test compiling route with DI dependencies."""
        executor = HandlerExecutor(service_container)

        async def handler(service: UserService):
            return service.get_user(1)

        route = Route(
            path="/users/1",
            method=HTTPMethod.GET,
            handler=handler,
            name="get_user",
            dependencies=["service"],
        )

        executor.compile_route(route)
        assert executor._route_key(route) in executor._execution_plans


# =============================================================================
# Path Parameter Conversion Tests
# =============================================================================


class TestPathParameterConversion:
    """Test path parameter type conversion."""

    @pytest.mark.asyncio
    async def test_convert_int_param(self, service_container: Container):
        """Test integer parameter conversion."""
        executor = HandlerExecutor(service_container)

        async def handler(user_id: int):
            return {"id": user_id, "type": type(user_id).__name__}

        route = Route(
            path="/users/{user_id}",
            method=HTTPMethod.GET,
            handler=handler,
            name="get_user",
            path_params=["user_id"],
        )

        executor.compile_route(route)

        request = make_mock_request(path_params={"user_id": "42"})
        response = await executor.execute_route(route, request, {"user_id": "42"})

        assert isinstance(response, JSONResponse)
        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["id"] == 42
        assert body["type"] == "int"

    @pytest.mark.asyncio
    async def test_convert_float_param(self, service_container: Container):
        """Test float parameter conversion."""
        executor = HandlerExecutor(service_container)

        async def handler(price: float):
            return {"price": price}

        route = Route(
            path="/items/{price}",
            method=HTTPMethod.GET,
            handler=handler,
            name="get_price",
            path_params=["price"],
        )

        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {"price": "19.99"})

        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["price"] == 19.99

    @pytest.mark.asyncio
    async def test_convert_bool_param(self, service_container: Container):
        """Test boolean parameter conversion."""
        executor = HandlerExecutor(service_container)

        async def handler(active: bool):
            return {"active": active}

        route = Route(
            path="/filter/{active}",
            method=HTTPMethod.GET,
            handler=handler,
            name="filter",
            path_params=["active"],
        )

        executor.compile_route(route)

        # Test 'true'
        response = await executor.execute_route(route, make_mock_request(), {"active": "true"})
        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["active"] is True

        # Test 'false'
        response = await executor.execute_route(route, make_mock_request(), {"active": "false"})
        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["active"] is False

    @pytest.mark.asyncio
    async def test_invalid_int_param_raises_http_exception(self, service_container: Container):
        """Test that invalid int param raises HTTPException with 400 status."""
        executor = HandlerExecutor(service_container)

        async def handler(user_id: int):
            return {"id": user_id}

        route = Route(
            path="/users/{user_id}",
            method=HTTPMethod.GET,
            handler=handler,
            name="get_user",
            path_params=["user_id"],
        )

        executor.compile_route(route)

        # HTTPException is raised during param conversion (before handler execution)
        # and is not caught by the handler executor's try block
        with pytest.raises(HTTPException) as exc_info:
            await executor.execute_route(route, make_mock_request(), {"user_id": "not_a_number"})

        exc = exc_info.value
        assert exc.status_code == 400  # type: ignore[union-attr]
        assert exc.detail is not None  # type: ignore[union-attr]
        assert "expected int" in exc.detail.lower()  # type: ignore[union-attr]


# =============================================================================
# DI Injection Tests
# =============================================================================


class TestDependencyInjection:
    """Test dependency injection in handlers."""

    @pytest.mark.asyncio
    async def test_inject_service(self, service_container: Container):
        """Test injecting a service from container."""
        executor = HandlerExecutor(service_container)

        async def handler(service: UserService):
            return service.get_user(123)

        route = Route(
            path="/users/123",
            method=HTTPMethod.GET,
            handler=handler,
            name="get_user",
            dependencies=["service"],
        )

        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["id"] == 123
        assert body["name"] == "User 123"


# =============================================================================
# Response Generation Tests
# =============================================================================


class TestResponseGeneration:
    """Test response generation from handler results."""

    @pytest.mark.asyncio
    async def test_dict_response(self, service_container: Container):
        """Test that dict is converted to JSONResponse."""
        executor = HandlerExecutor(service_container)

        async def handler():
            return {"key": "value"}

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert isinstance(response, JSONResponse)
        assert json.loads(response.body.decode()) == {"key": "value"}  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_list_response(self, service_container: Container):
        """Test that list is converted to JSONResponse."""
        executor = HandlerExecutor(service_container)

        async def handler():
            return [1, 2, 3]

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert json.loads(response.body.decode()) == [1, 2, 3]  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_none_response(self, service_container: Container):
        """Test that None returns 204 No Content."""
        executor = HandlerExecutor(service_container)

        async def handler():
            return None

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_response_passthrough(self, service_container: Container):
        """Test that Response objects are passed through."""
        executor = HandlerExecutor(service_container)

        async def handler():
            return Response(content="custom", media_type="text/plain", status_code=201)

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 201
        assert response.body == b"custom"

    @pytest.mark.asyncio
    async def test_pydantic_model_response(self, service_container: Container):
        """Test that Pydantic models are serialized."""
        executor = HandlerExecutor(service_container)

        class UserResponse(BaseModel):
            id: int
            name: str

        async def handler():
            return UserResponse(id=1, name="Test")

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["id"] == 1
        assert body["name"] == "Test"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling in handlers."""

    @pytest.mark.asyncio
    async def test_http_exception_handled(self, service_container: Container):
        """Test that HTTPException is properly handled."""
        executor = HandlerExecutor(service_container)

        async def handler():
            raise HTTPException(status_code=404, detail="Not found")

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 404
        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["detail"] == "Not found"

    @pytest.mark.asyncio
    async def test_generic_exception_returns_500(self, service_container: Container):
        """Test that generic exceptions return 500."""
        executor = HandlerExecutor(service_container)

        async def handler():
            raise ValueError("Something went wrong")

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_error_hides_details_in_production(self, service_container: Container):
        """Test that error details are hidden in production."""
        executor = HandlerExecutor(service_container)

        async def handler():
            raise ValueError("Secret error details")

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        # Should not contain the actual error message
        assert "Secret error details" not in body.get("detail", "")
        assert "unexpected error" in body.get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_error_shows_details_in_debug(self, debug_container: Container):
        """Test that error details are shown in debug mode."""
        executor = HandlerExecutor(debug_container)

        async def handler():
            raise ValueError("Debug error details")

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, name="test")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert "Debug error details" in body.get("detail", "")
        assert "traceback" in body


# =============================================================================
# Sync Handler Tests
# =============================================================================


class TestSyncHandlers:
    """Test synchronous handler support."""

    @pytest.mark.asyncio
    async def test_sync_handler_works(self, service_container: Container):
        """Test that sync handlers work correctly."""
        executor = HandlerExecutor(service_container)

        def sync_handler():
            return {"sync": True}

        route = Route(path="/sync", method=HTTPMethod.GET, handler=sync_handler, name="sync")
        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["sync"] is True
