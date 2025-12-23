"""
Integration tests for query parameter handling.

These tests verify:
- Query parameter detection in handler analysis
- Query parameter conversion and injection
- Validation constraints (ge, le, gt, lt, min_length, max_length, pattern)
- Default value handling
- Required parameter handling
- Alias support
"""

import json
from unittest.mock import MagicMock

import pytest
from starlette.datastructures import QueryParams
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from myfy.core.config import CoreSettings
from myfy.core.di import SINGLETON, Container
from myfy.web.handlers import HandlerExecutor
from myfy.web.params import Query, QueryParam
from myfy.web.routing import Router

pytestmark = pytest.mark.integration


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def container() -> Container:
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
    query_params: dict | None = None,
    method: str = "GET",
) -> MagicMock:
    """Create a mock Starlette request with query parameters."""
    request = MagicMock(spec=Request)
    request.method = method
    request.query_params = QueryParams(query_params or {})

    async def get_body():
        return b""

    async def get_json():
        return {}

    request.body = get_body
    request.json = get_json

    return request


# =============================================================================
# Query Parameter Detection Tests
# =============================================================================


class TestQueryParameterDetection:
    """Test query parameter detection in handler signature analysis."""

    def test_detect_query_param_with_default(self):
        """Test that Query(...) parameters are detected."""
        router = Router()

        @router.get("/search")
        async def search(q: str = Query(default="")):
            return {"q": q}

        routes = router.get_routes()
        route = routes[0]

        assert len(route.query_params) == 1
        assert route.query_params[0].name == "q"
        assert route.query_params[0].type_hint is str
        assert route.query_params[0].spec.default == ""

    def test_detect_required_query_param(self):
        """Test that required Query() parameters are detected."""
        router = Router()

        @router.get("/search")
        async def search(q: str = Query()):
            return {"q": q}

        routes = router.get_routes()
        route = routes[0]

        assert len(route.query_params) == 1
        assert route.query_params[0].spec.is_required is True

    def test_detect_multiple_query_params(self):
        """Test detection of multiple query parameters."""
        router = Router()

        @router.get("/search")
        async def search(
            q: str = Query(default=""),
            limit: int = Query(default=20),
            offset: int = Query(default=0),
        ):
            return {"q": q, "limit": limit, "offset": offset}

        routes = router.get_routes()
        route = routes[0]

        assert len(route.query_params) == 3
        param_names = [p.name for p in route.query_params]
        assert "q" in param_names
        assert "limit" in param_names
        assert "offset" in param_names

    def test_query_params_not_in_dependencies(self):
        """Test that query params are not treated as DI dependencies."""
        router = Router()

        @router.get("/search")
        async def search(q: str = Query(default="")):
            return {"q": q}

        routes = router.get_routes()
        route = routes[0]

        assert "q" not in route.dependencies
        assert len(route.query_params) == 1

    def test_mixed_query_and_path_params(self):
        """Test handler with both path and query parameters."""
        router = Router()

        @router.get("/users/{user_id}/posts")
        async def get_posts(
            user_id: int,
            limit: int = Query(default=10),
            include_hidden: bool = Query(default=False),
        ):
            return {"user_id": user_id}

        routes = router.get_routes()
        route = routes[0]

        assert "user_id" in route.path_params
        assert len(route.query_params) == 2
        assert "user_id" not in [p.name for p in route.query_params]

    def test_query_param_with_alias(self):
        """Test query parameter with alias."""
        router = Router()

        @router.get("/search")
        async def search(search_query: str = Query(default="", alias="q")):
            return {"q": search_query}

        routes = router.get_routes()
        route = routes[0]

        assert route.query_params[0].name == "search_query"
        assert route.query_params[0].alias == "q"
        assert route.query_params[0].query_name == "q"


# =============================================================================
# Query Parameter Injection Tests
# =============================================================================


class TestQueryParameterInjection:
    """Test query parameter injection into handlers."""

    @pytest.mark.asyncio
    async def test_inject_string_query_param(self, container: Container):
        """Test injecting a string query parameter."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/search")
        async def search(q: str = Query(default="")):
            return {"q": q}

        route = router.get_routes()[0]
        executor.compile_route(route)

        request = make_mock_request(query_params={"q": "hello"})
        response = await executor.execute_route(route, request, {})

        assert isinstance(response, JSONResponse)
        body = json.loads(response.body.decode())  # type: ignore[union-attr]  # type: ignore[union-attr]
        assert body["q"] == "hello"

    @pytest.mark.asyncio
    async def test_inject_int_query_param(self, container: Container):
        """Test injecting an integer query parameter."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/items")
        async def get_items(limit: int = Query(default=20)):
            return {"limit": limit, "type": type(limit).__name__}

        route = router.get_routes()[0]
        executor.compile_route(route)

        request = make_mock_request(query_params={"limit": "50"})
        response = await executor.execute_route(route, request, {})

        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["limit"] == 50
        assert body["type"] == "int"

    @pytest.mark.asyncio
    async def test_inject_float_query_param(self, container: Container):
        """Test injecting a float query parameter."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/items")
        async def get_items(price: float = Query(default=0.0)):
            return {"price": price}

        route = router.get_routes()[0]
        executor.compile_route(route)

        request = make_mock_request(query_params={"price": "19.99"})
        response = await executor.execute_route(route, request, {})

        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["price"] == 19.99

    @pytest.mark.asyncio
    async def test_inject_bool_query_param(self, container: Container):
        """Test injecting a boolean query parameter."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/items")
        async def get_items(include_hidden: bool = Query(default=False)):
            return {"include_hidden": include_hidden}

        route = router.get_routes()[0]
        executor.compile_route(route)

        # Test 'true'
        request = make_mock_request(query_params={"include_hidden": "true"})
        response = await executor.execute_route(route, request, {})
        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["include_hidden"] is True

        # Test '1'
        request = make_mock_request(query_params={"include_hidden": "1"})
        response = await executor.execute_route(route, request, {})
        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["include_hidden"] is True

        # Test 'false'
        request = make_mock_request(query_params={"include_hidden": "false"})
        response = await executor.execute_route(route, request, {})
        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["include_hidden"] is False

    @pytest.mark.asyncio
    async def test_use_default_when_param_missing(self, container: Container):
        """Test that default value is used when parameter is not provided."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/search")
        async def search(limit: int = Query(default=20)):
            return {"limit": limit}

        route = router.get_routes()[0]
        executor.compile_route(route)

        request = make_mock_request(query_params={})  # No limit provided
        response = await executor.execute_route(route, request, {})

        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["limit"] == 20

    @pytest.mark.asyncio
    async def test_required_param_missing_raises_error(self, container: Container):
        """Test that missing required parameter raises HTTPException."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/search")
        async def search(q: str = Query()):  # Required
            return {"q": q}

        route = router.get_routes()[0]
        executor.compile_route(route)

        request = make_mock_request(query_params={})  # No q provided

        with pytest.raises(HTTPException) as exc_info:
            await executor.execute_route(route, request, {})

        assert exc_info.value.status_code == 400  # type: ignore[union-attr]
        assert "required" in exc_info.value.detail  # type: ignore[union-attr].lower()

    @pytest.mark.asyncio
    async def test_alias_extraction(self, container: Container):
        """Test that alias is used for query string extraction."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/search")
        async def search(search_query: str = Query(default="", alias="q")):
            return {"q": search_query}

        route = router.get_routes()[0]
        executor.compile_route(route)

        # Use alias 'q' in query string
        request = make_mock_request(query_params={"q": "test search"})
        response = await executor.execute_route(route, request, {})

        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["q"] == "test search"


# =============================================================================
# Validation Tests
# =============================================================================


class TestQueryParameterValidation:
    """Test query parameter validation constraints."""

    @pytest.mark.asyncio
    async def test_ge_constraint_passes(self, container: Container):
        """Test that ge constraint passes for valid values."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/items")
        async def get_items(limit: int = Query(default=20, ge=1)):
            return {"limit": limit}

        route = router.get_routes()[0]
        executor.compile_route(route)

        request = make_mock_request(query_params={"limit": "5"})
        response = await executor.execute_route(route, request, {})

        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["limit"] == 5

    @pytest.mark.asyncio
    async def test_ge_constraint_fails(self, container: Container):
        """Test that ge constraint fails for invalid values."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/items")
        async def get_items(limit: int = Query(default=20, ge=1)):
            return {"limit": limit}

        route = router.get_routes()[0]
        executor.compile_route(route)

        request = make_mock_request(query_params={"limit": "0"})

        with pytest.raises(HTTPException) as exc_info:
            await executor.execute_route(route, request, {})

        assert exc_info.value.status_code == 400  # type: ignore[union-attr]
        assert ">=" in exc_info.value.detail  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_le_constraint_passes(self, container: Container):
        """Test that le constraint passes for valid values."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/items")
        async def get_items(limit: int = Query(default=20, le=100)):
            return {"limit": limit}

        route = router.get_routes()[0]
        executor.compile_route(route)

        request = make_mock_request(query_params={"limit": "50"})
        response = await executor.execute_route(route, request, {})

        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["limit"] == 50

    @pytest.mark.asyncio
    async def test_le_constraint_fails(self, container: Container):
        """Test that le constraint fails for invalid values."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/items")
        async def get_items(limit: int = Query(default=20, le=100)):
            return {"limit": limit}

        route = router.get_routes()[0]
        executor.compile_route(route)

        request = make_mock_request(query_params={"limit": "200"})

        with pytest.raises(HTTPException) as exc_info:
            await executor.execute_route(route, request, {})

        assert exc_info.value.status_code == 400  # type: ignore[union-attr]
        assert "<=" in exc_info.value.detail  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_combined_ge_le_constraints(self, container: Container):
        """Test combined ge and le constraints."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/items")
        async def get_items(limit: int = Query(default=20, ge=1, le=100)):
            return {"limit": limit}

        route = router.get_routes()[0]
        executor.compile_route(route)

        # Valid value
        request = make_mock_request(query_params={"limit": "50"})
        response = await executor.execute_route(route, request, {})
        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["limit"] == 50

        # Too low
        request = make_mock_request(query_params={"limit": "0"})
        with pytest.raises(HTTPException) as exc_info:
            await executor.execute_route(route, request, {})
        assert exc_info.value.status_code == 400  # type: ignore[union-attr]

        # Too high
        request = make_mock_request(query_params={"limit": "200"})
        with pytest.raises(HTTPException) as exc_info:
            await executor.execute_route(route, request, {})
        assert exc_info.value.status_code == 400  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_gt_constraint(self, container: Container):
        """Test gt (greater than) constraint."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/items")
        async def get_items(offset: int = Query(default=0, gt=0)):
            return {"offset": offset}

        route = router.get_routes()[0]
        executor.compile_route(route)

        # Equal value should fail (gt, not ge)
        request = make_mock_request(query_params={"offset": "0"})
        with pytest.raises(HTTPException) as exc_info:
            await executor.execute_route(route, request, {})
        assert exc_info.value.status_code == 400  # type: ignore[union-attr]
        assert ">" in exc_info.value.detail  # type: ignore[union-attr]

        # Greater value should pass
        request = make_mock_request(query_params={"offset": "1"})
        response = await executor.execute_route(route, request, {})
        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["offset"] == 1

    @pytest.mark.asyncio
    async def test_lt_constraint(self, container: Container):
        """Test lt (less than) constraint."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/items")
        async def get_items(priority: int = Query(default=5, lt=10)):
            return {"priority": priority}

        route = router.get_routes()[0]
        executor.compile_route(route)

        # Equal value should fail (lt, not le)
        request = make_mock_request(query_params={"priority": "10"})
        with pytest.raises(HTTPException) as exc_info:
            await executor.execute_route(route, request, {})
        assert exc_info.value.status_code == 400  # type: ignore[union-attr]
        assert "<" in exc_info.value.detail  # type: ignore[union-attr]

        # Lesser value should pass
        request = make_mock_request(query_params={"priority": "5"})
        response = await executor.execute_route(route, request, {})
        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["priority"] == 5

    @pytest.mark.asyncio
    async def test_min_length_constraint(self, container: Container):
        """Test min_length string constraint."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/search")
        async def search(q: str = Query(default="", min_length=3)):
            return {"q": q}

        route = router.get_routes()[0]
        executor.compile_route(route)

        # Too short
        request = make_mock_request(query_params={"q": "ab"})
        with pytest.raises(HTTPException) as exc_info:
            await executor.execute_route(route, request, {})
        assert exc_info.value.status_code == 400  # type: ignore[union-attr]
        assert "at least" in exc_info.value.detail  # type: ignore[union-attr].lower()

        # Valid length
        request = make_mock_request(query_params={"q": "abc"})
        response = await executor.execute_route(route, request, {})
        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["q"] == "abc"

    @pytest.mark.asyncio
    async def test_max_length_constraint(self, container: Container):
        """Test max_length string constraint."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/search")
        async def search(q: str = Query(default="", max_length=10)):
            return {"q": q}

        route = router.get_routes()[0]
        executor.compile_route(route)

        # Too long
        request = make_mock_request(query_params={"q": "a" * 15})
        with pytest.raises(HTTPException) as exc_info:
            await executor.execute_route(route, request, {})
        assert exc_info.value.status_code == 400  # type: ignore[union-attr]
        assert "at most" in exc_info.value.detail  # type: ignore[union-attr].lower()

        # Valid length
        request = make_mock_request(query_params={"q": "hello"})
        response = await executor.execute_route(route, request, {})
        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["q"] == "hello"

    @pytest.mark.asyncio
    async def test_pattern_constraint(self, container: Container):
        """Test pattern (regex) string constraint."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/users")
        async def get_users(email: str = Query(default="", pattern=r"^[\w.-]+@[\w.-]+\.\w+$")):
            return {"email": email}

        route = router.get_routes()[0]
        executor.compile_route(route)

        # Invalid email
        request = make_mock_request(query_params={"email": "not-an-email"})
        with pytest.raises(HTTPException) as exc_info:
            await executor.execute_route(route, request, {})
        assert exc_info.value.status_code == 400  # type: ignore[union-attr]
        assert "pattern" in exc_info.value.detail  # type: ignore[union-attr].lower()

        # Valid email
        request = make_mock_request(query_params={"email": "test@example.com"})
        response = await executor.execute_route(route, request, {})
        body = json.loads(response.body.decode())  # type: ignore[union-attr]
        assert body["email"] == "test@example.com"


# =============================================================================
# Type Conversion Error Tests
# =============================================================================


class TestTypeConversionErrors:
    """Test error handling for type conversion failures."""

    @pytest.mark.asyncio
    async def test_invalid_int_raises_error(self, container: Container):
        """Test that invalid int value raises HTTPException."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/items")
        async def get_items(limit: int = Query(default=20)):
            return {"limit": limit}

        route = router.get_routes()[0]
        executor.compile_route(route)

        request = make_mock_request(query_params={"limit": "not-a-number"})

        with pytest.raises(HTTPException) as exc_info:
            await executor.execute_route(route, request, {})

        assert exc_info.value.status_code == 400  # type: ignore[union-attr]
        assert "expected int" in exc_info.value.detail  # type: ignore[union-attr].lower()

    @pytest.mark.asyncio
    async def test_invalid_float_raises_error(self, container: Container):
        """Test that invalid float value raises HTTPException."""
        executor = HandlerExecutor(container)
        router = Router()

        @router.get("/items")
        async def get_items(price: float = Query(default=0.0)):
            return {"price": price}

        route = router.get_routes()[0]
        executor.compile_route(route)

        request = make_mock_request(query_params={"price": "not-a-float"})

        with pytest.raises(HTTPException) as exc_info:
            await executor.execute_route(route, request, {})

        assert exc_info.value.status_code == 400  # type: ignore[union-attr]
        assert "expected float" in exc_info.value.detail  # type: ignore[union-attr].lower()


# =============================================================================
# QueryParam Class Unit Tests
# =============================================================================


class TestQueryParamClass:
    """Unit tests for QueryParam class."""

    def test_is_required_with_ellipsis(self):
        """Test that ellipsis default makes param required."""
        param = QueryParam()  # default is ...
        assert param.is_required is True

    def test_is_not_required_with_default(self):
        """Test that providing a default makes param optional."""
        param = QueryParam(default="")
        assert param.is_required is False

        param = QueryParam(default=None)
        assert param.is_required is False

    def test_validate_required_with_none_raises(self):
        """Test that validating None for required param raises."""
        param = QueryParam()  # Required

        with pytest.raises(ValueError) as exc_info:
            param.validate(None, "test_param")

        assert "required" in str(exc_info.value).lower()

    def test_validate_optional_with_none_returns_default(self):
        """Test that validating None for optional param returns default."""
        param = QueryParam(default="default_value")

        result = param.validate(None, "test_param")
        assert result == "default_value"

    def test_validate_ge_constraint(self):
        """Test ge validation on numbers."""
        param = QueryParam(default=0, ge=5)

        # Valid
        assert param.validate(5, "test") == 5
        assert param.validate(10, "test") == 10

        # Invalid
        with pytest.raises(ValueError):
            param.validate(4, "test")

    def test_validate_le_constraint(self):
        """Test le validation on numbers."""
        param = QueryParam(default=0, le=10)

        # Valid
        assert param.validate(10, "test") == 10
        assert param.validate(5, "test") == 5

        # Invalid
        with pytest.raises(ValueError):
            param.validate(11, "test")

    def test_validate_gt_constraint(self):
        """Test gt validation on numbers."""
        param = QueryParam(default=0, gt=5)

        # Valid
        assert param.validate(6, "test") == 6

        # Invalid - equal is not allowed
        with pytest.raises(ValueError):
            param.validate(5, "test")

    def test_validate_lt_constraint(self):
        """Test lt validation on numbers."""
        param = QueryParam(default=0, lt=10)

        # Valid
        assert param.validate(9, "test") == 9

        # Invalid - equal is not allowed
        with pytest.raises(ValueError):
            param.validate(10, "test")

    def test_validate_min_length_constraint(self):
        """Test min_length validation on strings."""
        param = QueryParam(default="", min_length=3)

        # Valid
        assert param.validate("abc", "test") == "abc"

        # Invalid
        with pytest.raises(ValueError):
            param.validate("ab", "test")

    def test_validate_max_length_constraint(self):
        """Test max_length validation on strings."""
        param = QueryParam(default="", max_length=5)

        # Valid
        assert param.validate("hello", "test") == "hello"

        # Invalid
        with pytest.raises(ValueError):
            param.validate("toolong", "test")

    def test_validate_pattern_constraint(self):
        """Test pattern (regex) validation on strings."""
        param = QueryParam(default="", pattern=r"^\d{3}$")

        # Valid
        assert param.validate("123", "test") == "123"

        # Invalid
        with pytest.raises(ValueError):
            param.validate("12", "test")
        with pytest.raises(ValueError):
            param.validate("abc", "test")
