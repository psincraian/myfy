"""
Integration tests for myfy-web routing system.

These tests verify:
- Route registration and parsing
- Path parameter extraction
- Handler signature analysis
- Route method decorators
"""

from dataclasses import dataclass

import pytest
from pydantic import BaseModel

from myfy.core.config import BaseSettings
from myfy.web.routing import HTTPMethod, Router

pytestmark = pytest.mark.integration


# =============================================================================
# Test Models
# =============================================================================


class UserModel(BaseModel):
    """Pydantic model for testing body detection."""

    name: str
    email: str


@dataclass
class UserDataclass:
    """Dataclass for testing body detection."""

    name: str
    email: str


class AppSettings(BaseSettings):
    """Settings class for testing DI detection."""

    app_name: str = "test"


# =============================================================================
# Router Registration Tests
# =============================================================================


class TestRouterRegistration:
    """Test route registration functionality."""

    def test_register_simple_route(self):
        """Test registering a simple route."""
        router = Router()

        @router.get("/hello")
        async def hello():
            return {"message": "hello"}

        routes = router.get_routes()
        assert len(routes) == 1
        assert routes[0].path == "/hello"
        assert routes[0].method == HTTPMethod.GET
        assert routes[0].handler is hello

    def test_register_multiple_methods(self):
        """Test registering routes with different methods."""
        router = Router()

        @router.get("/users")
        async def list_users():
            return []

        @router.post("/users")
        async def create_user():
            return {}

        @router.put("/users/{id}")
        async def update_user(id: int):
            return {}

        @router.delete("/users/{id}")
        async def delete_user(id: int):
            return {}

        @router.patch("/users/{id}")
        async def patch_user(id: int):
            return {}

        routes = router.get_routes()
        assert len(routes) == 5

        methods = {r.method for r in routes}
        assert HTTPMethod.GET in methods
        assert HTTPMethod.POST in methods
        assert HTTPMethod.PUT in methods
        assert HTTPMethod.DELETE in methods
        assert HTTPMethod.PATCH in methods

    def test_register_with_name(self):
        """Test registering route with custom name."""
        router = Router()

        @router.get("/api/v1/users", name="get_users_v1")
        async def get_users():
            return []

        routes = router.get_routes()
        assert routes[0].name == "get_users_v1"

    def test_default_name_from_function(self):
        """Test that route name defaults to function name."""
        router = Router()

        @router.get("/test")
        async def my_handler_function():
            return {}

        routes = router.get_routes()
        assert routes[0].name == "my_handler_function"


# =============================================================================
# Path Parameter Tests
# =============================================================================


class TestPathParameterExtraction:
    """Test path parameter extraction from URL templates."""

    def test_single_path_param(self):
        """Test extraction of single path parameter."""
        router = Router()

        @router.get("/users/{user_id}")
        async def get_user(user_id: int):
            return {}

        routes = router.get_routes()
        assert routes[0].path_params == ["user_id"]

    def test_multiple_path_params(self):
        """Test extraction of multiple path parameters."""
        router = Router()

        @router.get("/users/{user_id}/posts/{post_id}")
        async def get_post(user_id: int, post_id: int):
            return {}

        routes = router.get_routes()
        assert routes[0].path_params == ["user_id", "post_id"]

    def test_path_without_params(self):
        """Test route without path parameters."""
        router = Router()

        @router.get("/static/path")
        async def static_handler():
            return {}

        routes = router.get_routes()
        assert routes[0].path_params == []

    def test_invalid_path_param_name_raises_error(self):
        """Test that invalid parameter names raise error."""
        router = Router()

        with pytest.raises(ValueError, match="Invalid path parameter name"):

            @router.get("/users/{123invalid}")
            async def invalid_handler():
                return {}

    def test_duplicate_path_param_raises_error(self):
        """Test that duplicate parameter names raise error."""
        router = Router()

        with pytest.raises(ValueError, match="Duplicate path parameter"):

            @router.get("/users/{id}/posts/{id}")
            async def duplicate_handler(id: int):
                return {}

    def test_underscore_in_param_name(self):
        """Test that underscores in param names are valid."""
        router = Router()

        @router.get("/users/{user_id}/posts/{post_id}")
        async def handler(user_id: int, post_id: int):
            return {}

        routes = router.get_routes()
        assert "user_id" in routes[0].path_params
        assert "post_id" in routes[0].path_params


# =============================================================================
# Handler Analysis Tests
# =============================================================================


class TestHandlerAnalysis:
    """Test handler signature analysis for DI and body detection."""

    def test_path_params_not_marked_as_dependencies(self):
        """Test that path params are not treated as DI dependencies."""
        router = Router()

        @router.get("/users/{user_id}")
        async def get_user(user_id: int):
            return {}

        routes = router.get_routes()
        assert "user_id" not in routes[0].dependencies
        assert "user_id" in routes[0].path_params

    def test_pydantic_model_detected_as_body(self):
        """Test that Pydantic models are detected as request body."""
        router = Router()

        @router.post("/users")
        async def create_user(user: UserModel):
            return {}

        routes = router.get_routes()
        assert routes[0].body_param == "user"
        assert "user" not in routes[0].dependencies

    def test_dataclass_detected_as_body(self):
        """Test that dataclasses are detected as request body."""
        router = Router()

        @router.post("/users")
        async def create_user(user: UserDataclass):
            return {}

        routes = router.get_routes()
        assert routes[0].body_param == "user"

    def test_dict_detected_as_body(self):
        """Test that dict type is detected as request body."""
        router = Router()

        @router.post("/data")
        async def create_data(data: dict):
            return {}

        routes = router.get_routes()
        assert routes[0].body_param == "data"

    def test_settings_not_detected_as_body(self):
        """Test that BaseSettings subclasses are DI dependencies, not body."""
        router = Router()

        @router.get("/config")
        async def get_config(settings: AppSettings):
            return {}

        routes = router.get_routes()
        assert routes[0].body_param is None
        assert "settings" in routes[0].dependencies

    def test_custom_class_detected_as_dependency(self):
        """Test that custom classes are treated as DI dependencies."""
        router = Router()

        class UserService:
            pass

        @router.get("/users")
        async def get_users(service: UserService):
            return []

        routes = router.get_routes()
        assert "service" in routes[0].dependencies
        assert routes[0].body_param is None

    def test_mixed_params(self):
        """Test handler with path params, body, and DI dependencies."""
        router = Router()

        class UserService:
            pass

        @router.put("/users/{user_id}")
        async def update_user(user_id: int, user: UserModel, service: UserService):
            return {}

        routes = router.get_routes()
        route = routes[0]

        assert "user_id" in route.path_params
        assert route.body_param == "user"
        assert "service" in route.dependencies
        assert "user_id" not in route.dependencies
        assert "user" not in route.dependencies


# =============================================================================
# Route Object Tests
# =============================================================================


class TestRouteObject:
    """Test Route dataclass behavior."""

    def test_route_repr(self):
        """Test Route string representation."""
        router = Router()

        @router.get("/users/{id}")
        async def get_user(id: int):
            return {}

        routes = router.get_routes()
        repr_str = repr(routes[0])

        assert "GET" in repr_str
        assert "/users/{id}" in repr_str
        assert "get_user" in repr_str

    def test_route_equality(self):
        """Test that routes are distinct objects."""
        router = Router()

        @router.get("/a")
        async def handler_a():
            return {}

        @router.get("/b")
        async def handler_b():
            return {}

        routes = router.get_routes()
        assert routes[0] is not routes[1]


# =============================================================================
# Router State Tests
# =============================================================================


class TestRouterState:
    """Test Router state management."""

    def test_get_routes_returns_copy(self):
        """Test that get_routes returns a copy."""
        router = Router()

        @router.get("/test")
        async def handler():
            return {}

        routes1 = router.get_routes()
        routes2 = router.get_routes()

        assert routes1 is not routes2
        assert routes1 == routes2

    def test_router_repr(self):
        """Test Router string representation."""
        router = Router()

        @router.get("/a")
        async def a():
            return {}

        @router.get("/b")
        async def b():
            return {}

        repr_str = repr(router)
        assert "Router" in repr_str
        assert "2" in repr_str  # 2 routes

    def test_add_route_directly(self):
        """Test adding route via add_route method."""
        router = Router()

        async def my_handler():
            return {}

        route = router.add_route("/direct", my_handler, HTTPMethod.GET, name="direct")

        assert route.path == "/direct"
        assert route.name == "direct"
        assert len(router.get_routes()) == 1
