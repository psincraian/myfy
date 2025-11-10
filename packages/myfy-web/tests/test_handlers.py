"""
Tests for handler execution with dependency injection.

Tests handler compilation, parameter injection, and error handling.
"""

import pytest
from pydantic import BaseModel
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.testclient import TestClient

from myfy.core.config import CoreSettings
from myfy.core.di.container import Container
from myfy.core.di.scopes import SINGLETON
from myfy.web.context import RequestContext
from myfy.web.handlers import HandlerExecutor
from myfy.web.routing import HTTPMethod, Route


class User(BaseModel):
    """Test model."""

    name: str
    email: str


class Database:
    """Mock database service."""

    def __init__(self):
        self.connected = True


class TestHandlerCompilation:
    """Test handler compilation."""

    def test_compile_simple_handler(self):
        """Should compile handler without dependencies."""
        container = Container()
        executor = HandlerExecutor(container)

        def handler():
            return {"message": "hello"}

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler)
        executor.compile_route(route)

        assert executor._route_key(route) in executor._execution_plans

    def test_compile_handler_with_path_params(self):
        """Should compile handler with path parameters."""
        container = Container()
        executor = HandlerExecutor(container)

        def handler(user_id: int):
            return {"user_id": user_id}

        route = Route(
            path="/users/{user_id}", method=HTTPMethod.GET, handler=handler, path_params=["user_id"]
        )
        executor.compile_route(route)

        assert executor._route_key(route) in executor._execution_plans

    def test_compile_handler_with_dependencies(self):
        """Should compile handler with DI dependencies."""
        container = Container()
        container.register(Database, lambda: Database(), scope=SINGLETON)
        container.compile()

        executor = HandlerExecutor(container)

        def handler(db: Database):
            return {"connected": db.connected}

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, dependencies=["db"])
        executor.compile_route(route)

        assert executor._route_key(route) in executor._execution_plans


class TestHandlerExecution:
    """Test handler execution."""

    @pytest.mark.asyncio
    async def test_execute_simple_handler(self):
        """Should execute simple handler."""
        container = Container()
        container.compile()
        executor = HandlerExecutor(container)

        def handler():
            return {"message": "hello"}

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler)
        executor.compile_route(route)

        # Create mock request
        from starlette.applications import Starlette

        app = Starlette()
        client = TestClient(app)
        request = Request({"type": "http", "method": "GET", "path": "/test"}, client)

        response = await executor.execute_route(route, request, {})

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_execute_async_handler(self):
        """Should execute async handler."""
        container = Container()
        container.compile()
        executor = HandlerExecutor(container)

        async def handler():
            return {"message": "hello"}

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler)
        executor.compile_route(route)

        from starlette.applications import Starlette

        app = Starlette()
        client = TestClient(app)
        request = Request({"type": "http", "method": "GET", "path": "/test"}, client)

        response = await executor.execute_route(route, request, {})

        assert isinstance(response, JSONResponse)

    @pytest.mark.asyncio
    async def test_execute_handler_with_path_params(self):
        """Should inject path parameters."""
        container = Container()
        container.compile()
        executor = HandlerExecutor(container)

        def handler(user_id: int):
            return {"user_id": user_id}

        route = Route(
            path="/users/{user_id}", method=HTTPMethod.GET, handler=handler, path_params=["user_id"]
        )
        executor.compile_route(route)

        from starlette.applications import Starlette

        app = Starlette()
        client = TestClient(app)
        request = Request({"type": "http", "method": "GET", "path": "/users/123"}, client)

        response = await executor.execute_route(route, request, {"user_id": "123"})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_execute_handler_with_di_dependency(self):
        """Should inject DI dependencies."""
        container = Container()
        container.register(Database, lambda: Database(), scope=SINGLETON)
        container.compile()

        executor = HandlerExecutor(container)

        def handler(db: Database):
            return {"connected": db.connected}

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, dependencies=["db"])
        executor.compile_route(route)

        from starlette.applications import Starlette

        app = Starlette()
        client = TestClient(app)
        request = Request({"type": "http", "method": "GET", "path": "/test"}, client)

        response = await executor.execute_route(route, request, {})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_execute_handler_not_compiled_raises_error(self):
        """Should raise error for uncompiled route."""
        container = Container()
        executor = HandlerExecutor(container)

        def handler():
            return {}

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler)
        # Don't compile

        from starlette.applications import Starlette

        app = Starlette()
        client = TestClient(app)
        request = Request({"type": "http", "method": "GET", "path": "/test"}, client)

        with pytest.raises(RuntimeError, match="not compiled"):
            await executor.execute_route(route, request, {})


class TestParameterConversion:
    """Test parameter type conversion."""

    def test_convert_int_param(self):
        """Should convert string to int."""
        container = Container()
        executor = HandlerExecutor(container)

        result = executor._convert_param("123", int, "id")
        assert result == 123
        assert isinstance(result, int)

    def test_convert_float_param(self):
        """Should convert string to float."""
        container = Container()
        executor = HandlerExecutor(container)

        result = executor._convert_param("3.14", float, "value")
        assert result == 3.14
        assert isinstance(result, float)

    def test_convert_bool_param(self):
        """Should convert string to bool."""
        container = Container()
        executor = HandlerExecutor(container)

        assert executor._convert_param("true", bool, "flag") is True
        assert executor._convert_param("1", bool, "flag") is True
        assert executor._convert_param("yes", bool, "flag") is True
        assert executor._convert_param("false", bool, "flag") is False
        assert executor._convert_param("0", bool, "flag") is False

    def test_convert_str_param(self):
        """Should convert to string."""
        container = Container()
        executor = HandlerExecutor(container)

        result = executor._convert_param("hello", str, "name")
        assert result == "hello"
        assert isinstance(result, str)

    def test_convert_invalid_int_raises_error(self):
        """Should raise HTTPException for invalid int."""
        container = Container()
        executor = HandlerExecutor(container)

        with pytest.raises(HTTPException) as exc_info:
            executor._convert_param("abc", int, "id")

        assert exc_info.value.status_code == 400
        assert "Invalid value" in exc_info.value.detail


class TestBodyParsing:
    """Test request body parsing."""

    @pytest.mark.asyncio
    async def test_parse_dict_body(self):
        """Should parse JSON to dict."""
        container = Container()
        executor = HandlerExecutor(container)

        from starlette.applications import Starlette

        app = Starlette()
        client = TestClient(app)
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/test",
                "headers": [(b"content-type", b"application/json")],
            },
            client,
        )

        # Mock JSON body
        request._body = b'{"name": "test"}'

        result = await executor._parse_body(request, dict)
        assert result == {"name": "test"}

    @pytest.mark.asyncio
    async def test_parse_pydantic_model_body(self):
        """Should parse and validate Pydantic model."""
        container = Container()
        executor = HandlerExecutor(container)

        from starlette.applications import Starlette

        app = Starlette()
        client = TestClient(app)
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/test",
                "headers": [(b"content-type", b"application/json")],
            },
            client,
        )

        request._body = b'{"name": "John", "email": "john@example.com"}'

        result = await executor._parse_body(request, User)
        assert isinstance(result, User)
        assert result.name == "John"
        assert result.email == "john@example.com"

    @pytest.mark.asyncio
    async def test_parse_invalid_pydantic_model_raises_error(self):
        """Should raise HTTPException for invalid Pydantic data."""
        container = Container()
        executor = HandlerExecutor(container)

        from starlette.applications import Starlette

        app = Starlette()
        client = TestClient(app)
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/test",
                "headers": [(b"content-type", b"application/json")],
            },
            client,
        )

        request._body = b'{"name": "John"}'  # Missing required 'email'

        with pytest.raises(HTTPException) as exc_info:
            await executor._parse_body(request, User)

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_parse_invalid_json_raises_error(self):
        """Should raise HTTPException for invalid JSON."""
        container = Container()
        executor = HandlerExecutor(container)

        from starlette.applications import Starlette

        app = Starlette()
        client = TestClient(app)
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/test",
                "headers": [(b"content-type", b"application/json")],
            },
            client,
        )

        request._body = b"{invalid json}"

        with pytest.raises(HTTPException) as exc_info:
            await executor._parse_body(request, dict)

        assert exc_info.value.status_code == 400


class TestResponseGeneration:
    """Test response generation."""

    def test_make_response_from_dict(self):
        """Should create JSONResponse from dict."""
        container = Container()
        executor = HandlerExecutor(container)

        response = executor._make_response({"message": "hello"})

        assert isinstance(response, JSONResponse)

    def test_make_response_from_list(self):
        """Should create JSONResponse from list."""
        container = Container()
        executor = HandlerExecutor(container)

        response = executor._make_response([1, 2, 3])

        assert isinstance(response, JSONResponse)

    def test_make_response_from_pydantic_model(self):
        """Should create JSONResponse from Pydantic model."""
        container = Container()
        executor = HandlerExecutor(container)

        user = User(name="John", email="john@example.com")
        response = executor._make_response(user)

        assert isinstance(response, JSONResponse)

    def test_make_response_from_response_object(self):
        """Should return Response object as-is."""
        container = Container()
        executor = HandlerExecutor(container)

        custom_response = Response(content="test", status_code=201)
        response = executor._make_response(custom_response)

        assert response is custom_response

    def test_make_response_from_none(self):
        """Should create 204 No Content for None."""
        container = Container()
        executor = HandlerExecutor(container)

        response = executor._make_response(None)

        assert isinstance(response, Response)
        assert response.status_code == 204

    def test_make_response_from_string(self):
        """Should create text response from string."""
        container = Container()
        executor = HandlerExecutor(container)

        response = executor._make_response("hello")

        assert isinstance(response, (Response, JSONResponse))


class TestErrorHandling:
    """Test error handling."""

    def test_make_error_response_debug_mode(self):
        """Should include traceback in debug mode."""
        container = Container()
        container.register(CoreSettings, lambda: CoreSettings(debug=True), scope=SINGLETON)
        container.compile()

        executor = HandlerExecutor(container)

        error = ValueError("Test error")
        response = executor._make_error_response(error)

        assert response.status_code == 500
        # In debug mode, should have traceback
        assert "traceback" in response.body.decode()

    def test_make_error_response_production_mode(self):
        """Should hide details in production mode."""
        container = Container()
        container.register(CoreSettings, lambda: CoreSettings(debug=False), scope=SINGLETON)
        container.compile()

        executor = HandlerExecutor(container)

        error = ValueError("Test error")
        response = executor._make_error_response(error)

        assert response.status_code == 500
        body = response.body.decode()
        # Should not include actual error message
        assert "Test error" not in body
        assert "Internal Server Error" in body

    def test_make_error_response_no_settings(self):
        """Should default to production mode if settings unavailable."""
        container = Container()
        container.compile()

        executor = HandlerExecutor(container)

        error = ValueError("Test error")
        response = executor._make_error_response(error)

        assert response.status_code == 500
        # Should default to safe/production mode
        body = response.body.decode()
        assert "traceback" not in body


class TestRequestContextInjection:
    """Test request context injection."""

    @pytest.mark.asyncio
    async def test_inject_request_object(self):
        """Should inject Request object."""
        container = Container()
        container.compile()
        executor = HandlerExecutor(container)

        def handler(request: Request):
            return {"path": request.url.path}

        route = Route(
            path="/test", method=HTTPMethod.GET, handler=handler, dependencies=["request"]
        )
        executor.compile_route(route)

        from starlette.applications import Starlette

        app = Starlette()
        client = TestClient(app)
        request = Request({"type": "http", "method": "GET", "path": "/test"}, client)

        response = await executor.execute_route(route, request, {})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_inject_request_context(self):
        """Should inject RequestContext object."""
        from myfy.web.context import set_request_context

        container = Container()
        container.compile()
        executor = HandlerExecutor(container)

        def handler(ctx: RequestContext):
            return {"method": ctx.method}

        route = Route(path="/test", method=HTTPMethod.GET, handler=handler, dependencies=["ctx"])
        executor.compile_route(route)

        from starlette.applications import Starlette

        app = Starlette()
        client = TestClient(app)
        request = Request({"type": "http", "method": "GET", "path": "/test"}, client)

        # Set up request context
        set_request_context(RequestContext(request))

        response = await executor.execute_route(route, request, {})

        assert response.status_code == 200
