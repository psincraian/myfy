"""
Tests for the routing system.

Tests route registration, path parameter extraction, and handler analysis.
"""

import pytest
from pydantic import BaseModel

from myfy.web.routing import HTTPMethod, Router


class User(BaseModel):
    """Test model for request body."""

    name: str
    email: str


class Database:
    """Mock database for DI testing."""


class TestRouteRegistration:
    """Test route registration."""

    def test_add_route(self):
        """Should register a route."""
        router = Router()

        def handler():
            return {"message": "hello"}

        route = router.add_route("/hello", handler, HTTPMethod.GET)

        assert route.path == "/hello"
        assert route.method == HTTPMethod.GET
        assert route.handler is handler
        assert len(router.get_routes()) == 1

    def test_add_route_with_name(self):
        """Should register route with name."""
        router = Router()

        def handler():
            return {}

        route = router.add_route("/test", handler, HTTPMethod.GET, name="test_route")

        assert route.name == "test_route"

    def test_add_route_infers_name_from_function(self):
        """Should infer name from function name."""
        router = Router()

        def my_handler():
            return {}

        route = router.add_route("/test", my_handler, HTTPMethod.GET)

        assert route.name == "my_handler"

    def test_get_routes_returns_copy(self):
        """Should return copy of routes list."""
        router = Router()

        def handler():
            return {}

        router.add_route("/test", handler, HTTPMethod.GET)

        routes = router.get_routes()
        routes.clear()

        # Original should be unchanged
        assert len(router.get_routes()) == 1


class TestRouteDecorators:
    """Test route decorator methods."""

    def test_get_decorator(self):
        """Should register GET route."""
        router = Router()

        @router.get("/users")
        def get_users():
            return []

        routes = router.get_routes()
        assert len(routes) == 1
        assert routes[0].method == HTTPMethod.GET
        assert routes[0].path == "/users"

    def test_post_decorator(self):
        """Should register POST route."""
        router = Router()

        @router.post("/users")
        def create_user():
            return {}

        routes = router.get_routes()
        assert routes[0].method == HTTPMethod.POST

    def test_put_decorator(self):
        """Should register PUT route."""
        router = Router()

        @router.put("/users/{id}")
        def update_user():
            return {}

        routes = router.get_routes()
        assert routes[0].method == HTTPMethod.PUT

    def test_delete_decorator(self):
        """Should register DELETE route."""
        router = Router()

        @router.delete("/users/{id}")
        def delete_user():
            return {}

        routes = router.get_routes()
        assert routes[0].method == HTTPMethod.DELETE

    def test_patch_decorator(self):
        """Should register PATCH route."""
        router = Router()

        @router.patch("/users/{id}")
        def patch_user():
            return {}

        routes = router.get_routes()
        assert routes[0].method == HTTPMethod.PATCH

    def test_decorator_preserves_function(self):
        """Should preserve original function."""
        router = Router()

        @router.get("/test")
        def handler():
            return "test"

        # Function should still be callable
        result = handler()
        assert result == "test"

    def test_multiple_routes(self):
        """Should register multiple routes."""
        router = Router()

        @router.get("/users")
        def get_users():
            return []

        @router.post("/users")
        def create_user():
            return {}

        @router.get("/users/{id}")
        def get_user():
            return {}

        routes = router.get_routes()
        assert len(routes) == 3


class TestPathParameterExtraction:
    """Test path parameter extraction."""

    def test_extract_single_path_param(self):
        """Should extract single path parameter."""
        router = Router()

        def handler():
            return {}

        route = router.add_route("/users/{user_id}", handler, HTTPMethod.GET)

        assert route.path_params == ["user_id"]

    def test_extract_multiple_path_params(self):
        """Should extract multiple path parameters."""
        router = Router()

        def handler():
            return {}

        route = router.add_route("/users/{user_id}/posts/{post_id}", handler, HTTPMethod.GET)

        assert route.path_params == ["user_id", "post_id"]

    def test_no_path_params(self):
        """Should handle routes without parameters."""
        router = Router()

        def handler():
            return {}

        route = router.add_route("/users", handler, HTTPMethod.GET)

        assert route.path_params == []

    def test_invalid_path_param_name_raises_error(self):
        """Should raise error for invalid parameter names."""
        router = Router()

        def handler():
            return {}

        # Invalid characters in param name
        with pytest.raises(ValueError, match="Invalid path parameter name"):
            router.add_route("/users/{user-id}", handler, HTTPMethod.GET)

    def test_duplicate_path_param_raises_error(self):
        """Should raise error for duplicate parameters."""
        router = Router()

        def handler():
            return {}

        with pytest.raises(ValueError, match="Duplicate path parameter"):
            router.add_route("/users/{id}/posts/{id}", handler, HTTPMethod.GET)

    def test_path_param_name_validation(self):
        """Should validate parameter names are valid identifiers."""
        router = Router()

        def handler():
            return {}

        # Valid names
        router.add_route("/a/{id}", handler, HTTPMethod.GET)
        router.add_route("/b/{user_id}", handler, HTTPMethod.GET)
        router.add_route("/c/{_private}", handler, HTTPMethod.GET)

        # Invalid names
        with pytest.raises(ValueError):
            router.add_route("/d/{123}", handler, HTTPMethod.GET)

        with pytest.raises(ValueError):
            router.add_route("/e/{my-param}", handler, HTTPMethod.GET)


class TestHandlerAnalysis:
    """Test handler signature analysis."""

    def test_analyze_handler_with_path_params(self):
        """Should identify path parameters in handler."""
        router = Router()

        def handler(user_id: int):
            return {}

        route = router.add_route("/users/{user_id}", handler, HTTPMethod.GET)

        assert "user_id" in route.path_params
        assert "user_id" not in route.dependencies

    def test_analyze_handler_with_body_param(self):
        """Should identify request body parameter."""
        router = Router()

        def handler(user: User):
            return {}

        route = router.add_route("/users", handler, HTTPMethod.POST)

        assert route.body_param == "user"
        assert "user" not in route.dependencies

    def test_analyze_handler_with_dict_body(self):
        """Should identify dict as body parameter."""
        router = Router()

        def handler(data: dict):
            return {}

        route = router.add_route("/data", handler, HTTPMethod.POST)

        assert route.body_param == "data"

    def test_analyze_handler_with_list_body(self):
        """Should identify list as body parameter."""
        router = Router()

        def handler(items: list):
            return {}

        route = router.add_route("/items", handler, HTTPMethod.POST)

        assert route.body_param == "items"

    def test_analyze_handler_with_di_dependencies(self):
        """Should identify DI dependencies."""
        router = Router()

        def handler(db: Database):
            return {}

        route = router.add_route("/test", handler, HTTPMethod.GET)

        assert "db" in route.dependencies
        assert route.body_param is None

    def test_analyze_handler_mixed_params(self):
        """Should correctly classify mixed parameters."""
        router = Router()

        def handler(user_id: int, user: User, db: Database):
            return {}

        route = router.add_route("/users/{user_id}", handler, HTTPMethod.PUT)

        assert "user_id" in route.path_params
        assert route.body_param == "user"
        assert "db" in route.dependencies

    def test_analyze_handler_with_settings_as_dependency(self):
        """Should treat BaseSettings subclasses as DI dependencies, not body."""
        from myfy.core.config import BaseSettings

        class AppSettings(BaseSettings):
            app_name: str = "test"

        router = Router()

        def handler(settings: AppSettings):
            return {}

        route = router.add_route("/test", handler, HTTPMethod.GET)

        # Settings should be a DI dependency, not body
        assert "settings" in route.dependencies
        assert route.body_param is None


class TestRouteRepresentation:
    """Test route string representation."""

    def test_route_repr(self):
        """Should have useful string representation."""
        router = Router()

        def my_handler():
            return {}

        route = router.add_route("/users/{id}", my_handler, HTTPMethod.GET)

        repr_str = repr(route)
        assert "GET" in repr_str
        assert "/users/{id}" in repr_str
        assert "my_handler" in repr_str

    def test_router_repr(self):
        """Should show number of routes."""
        router = Router()

        assert "routes=0" in repr(router)

        router.add_route("/test", dict, HTTPMethod.GET)
        assert "routes=1" in repr(router)


class TestGlobalRouter:
    """Test global router instance."""

    def test_global_router_available(self):
        """Should provide global router instance."""
        from myfy.web.routing import route

        assert isinstance(route, Router)

    def test_global_router_can_register_routes(self):
        """Should be able to use global router."""
        from myfy.web.routing import route

        # Note: This test might interfere with other tests if run in parallel
        # In a real scenario, you'd want to clear routes between tests
        initial_count = len(route.get_routes())

        @route.get("/global-test")
        def test_handler():
            return {}

        assert len(route.get_routes()) == initial_count + 1
