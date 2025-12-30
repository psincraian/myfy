"""
Integration tests for AuthModule.

Tests verify:
- Anonymous type always succeeds
- Authenticated type returns 401 when None
- Custom protected types with custom status codes
- Provider override functionality
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from starlette.requests import Request

from myfy.core.config import CoreSettings
from myfy.core.di import REQUEST, SINGLETON, Container, ScopeContext
from myfy.web.auth import Anonymous, Authenticated, AuthModule
from myfy.web.auth.registry import ProtectedTypesRegistry
from myfy.web.handlers import HandlerExecutor
from myfy.web.routing import HTTPMethod, Route

pytestmark = pytest.mark.integration


# =============================================================================
# Test User Types
# =============================================================================


@dataclass
class User(Authenticated):
    """Test user type."""

    email: str


@dataclass
class AdminUser(User):
    """Test admin user type."""

    permissions: list[str] | None = None


@dataclass
class MyAnonymous(Anonymous):
    """Custom anonymous with extra data."""

    ip: str


# =============================================================================
# Fixtures
# =============================================================================


def make_mock_request() -> Request:
    """Create a minimal mock request."""
    from unittest.mock import MagicMock

    request = MagicMock(spec=Request)
    request.headers = {}
    return request


@pytest.fixture
def request_scope() -> Iterator[dict]:
    """Initialize and clean up a request scope for testing."""
    bag = ScopeContext.init_request_scope()
    yield bag
    ScopeContext.clear_request_bag()


@pytest.fixture
def base_container() -> Container:
    """Container with core settings."""
    container = Container()
    container.register(
        type_=CoreSettings,
        factory=lambda: CoreSettings(debug=False),
        scope=SINGLETON,
    )
    return container


# =============================================================================
# Anonymous Type Tests
# =============================================================================


class TestAnonymousType:
    """Test Anonymous type behavior."""

    @pytest.mark.asyncio
    async def test_anonymous_always_succeeds(self, base_container: Container, request_scope):
        """Anonymous type should always be available."""
        # Configure auth module with default anonymous
        auth_module = AuthModule()
        auth_module.configure(base_container)
        base_container.compile()

        executor = HandlerExecutor(base_container)

        async def handler(identity: Anonymous):
            return {"type": "anonymous"}

        route = Route(
            path="/public",
            method=HTTPMethod.GET,
            handler=handler,
            name="public",
            dependencies=["identity"],
        )

        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 200
        body = json.loads(response.body.decode())
        assert body["type"] == "anonymous"

    @pytest.mark.asyncio
    async def test_custom_anonymous_provider(self, base_container: Container, request_scope):
        """Custom anonymous provider should be used."""

        def my_anonymous() -> MyAnonymous:
            return MyAnonymous(ip="127.0.0.1")

        auth_module = AuthModule(anonymous_provider=my_anonymous)
        auth_module.configure(base_container)

        # Also register MyAnonymous since that's what handler asks for
        base_container.register(
            type_=MyAnonymous,
            factory=my_anonymous,
            scope=REQUEST,
        )

        base_container.compile()

        executor = HandlerExecutor(base_container)

        async def handler(identity: MyAnonymous):
            return {"ip": identity.ip}

        route = Route(
            path="/info",
            method=HTTPMethod.GET,
            handler=handler,
            name="info",
            dependencies=["identity"],
        )

        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 200
        body = json.loads(response.body.decode())
        assert body["ip"] == "127.0.0.1"


# =============================================================================
# Authenticated Type Tests
# =============================================================================


class TestAuthenticatedType:
    """Test Authenticated type behavior."""

    @pytest.mark.asyncio
    async def test_authenticated_returns_401_when_none(
        self, base_container: Container, request_scope
    ):
        """Authenticated type should return 401 when provider returns None."""

        def no_auth() -> User | None:
            return None

        auth_module = AuthModule(
            authenticated_provider=no_auth,
            protected_types={User: 401},
        )
        auth_module.configure(base_container)

        # Register User provider that returns None
        base_container.register(
            type_=User,
            factory=no_auth,
            scope=REQUEST,
        )

        base_container.compile()

        executor = HandlerExecutor(base_container)

        async def handler(user: User):
            return {"id": user.id}

        route = Route(
            path="/profile",
            method=HTTPMethod.GET,
            handler=handler,
            name="profile",
            dependencies=["user"],
        )

        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 401
        body = json.loads(response.body.decode())
        assert body["detail"] == "Authentication required"

    @pytest.mark.asyncio
    async def test_authenticated_succeeds_when_valid(
        self, base_container: Container, request_scope
    ):
        """Authenticated type should succeed when provider returns user."""

        def valid_auth() -> User:
            return User(id="123", email="test@example.com")

        auth_module = AuthModule(
            authenticated_provider=valid_auth,
            protected_types={User: 401},
        )
        auth_module.configure(base_container)

        # Register User provider
        base_container.register(
            type_=User,
            factory=valid_auth,
            scope=REQUEST,
        )

        base_container.compile()

        executor = HandlerExecutor(base_container)

        async def handler(user: User):
            return {"id": user.id, "email": user.email}

        route = Route(
            path="/profile",
            method=HTTPMethod.GET,
            handler=handler,
            name="profile",
            dependencies=["user"],
        )

        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 200
        body = json.loads(response.body.decode())
        assert body["id"] == "123"
        assert body["email"] == "test@example.com"


# =============================================================================
# Custom Protected Types Tests
# =============================================================================


class TestCustomProtectedTypes:
    """Test custom protected types with custom status codes."""

    @pytest.mark.asyncio
    async def test_custom_type_returns_configured_code(
        self, base_container: Container, request_scope
    ):
        """Custom types should return configured status codes."""

        def no_admin() -> AdminUser | None:
            return None

        auth_module = AuthModule(
            protected_types={
                User: 401,
                AdminUser: 403,
            },
        )
        auth_module.configure(base_container)

        # Register AdminUser provider that returns None
        base_container.register(
            type_=AdminUser,
            factory=no_admin,
            scope=REQUEST,
        )

        base_container.compile()

        executor = HandlerExecutor(base_container)

        async def handler(admin: AdminUser):
            return {"admin": True}

        route = Route(
            path="/admin",
            method=HTTPMethod.GET,
            handler=handler,
            name="admin",
            dependencies=["admin"],
        )

        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 403
        body = json.loads(response.body.decode())
        assert body["detail"] == "Forbidden"

    @pytest.mark.asyncio
    async def test_subclass_uses_parent_code_if_not_configured(
        self, base_container: Container, request_scope
    ):
        """Subclass should use parent's status code if not explicitly configured."""

        def no_admin() -> AdminUser | None:
            return None

        # Only configure User, not AdminUser
        auth_module = AuthModule(
            protected_types={
                User: 401,
            },
        )
        auth_module.configure(base_container)

        base_container.register(
            type_=AdminUser,
            factory=no_admin,
            scope=REQUEST,
        )

        base_container.compile()

        executor = HandlerExecutor(base_container)

        async def handler(admin: AdminUser):
            return {"admin": True}

        route = Route(
            path="/admin",
            method=HTTPMethod.GET,
            handler=handler,
            name="admin",
            dependencies=["admin"],
        )

        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        # AdminUser is subclass of User, so should use User's 401
        assert response.status_code == 401


# =============================================================================
# No AuthModule Tests
# =============================================================================


class TestNoAuthModule:
    """Test behavior when AuthModule is not configured."""

    @pytest.mark.asyncio
    async def test_no_auth_module_none_not_intercepted(
        self, base_container: Container, request_scope
    ):
        """Without AuthModule, None values are not intercepted (normal DI behavior)."""

        def returns_none() -> User | None:
            return None

        # No AuthModule configured - register User provider
        base_container.register(
            type_=User,
            factory=returns_none,
            scope=REQUEST,
        )
        base_container.compile()

        executor = HandlerExecutor(base_container)

        # Handler asks for User (not Optional), so it gets None
        async def handler(user: User):
            # This would fail at runtime if user is None
            # But without AuthModule, the framework doesn't intercept
            return {"user_id": user.id if user else None}

        route = Route(
            path="/profile",
            method=HTTPMethod.GET,
            handler=handler,
            name="profile",
            dependencies=["user"],
        )

        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        # Without AuthModule, None passes through (no protection)
        # The handler receives None and would fail if it tries to use it
        assert response.status_code == 200
        body = json.loads(response.body.decode())
        assert body["user_id"] is None


# =============================================================================
# Registry Tests
# =============================================================================


class TestProtectedTypesRegistry:
    """Test ProtectedTypesRegistry behavior."""

    def test_direct_match(self):
        """Direct type match should return configured code."""
        registry = ProtectedTypesRegistry({User: 401, AdminUser: 403})

        assert registry.get_status_code(User) == 401
        assert registry.get_status_code(AdminUser) == 403

    def test_inheritance_match(self):
        """Subclass should match parent if not directly configured."""
        registry = ProtectedTypesRegistry({User: 401})

        # AdminUser extends User
        assert registry.get_status_code(AdminUser) == 401

    def test_no_match_returns_none(self):
        """Non-protected types should return None."""
        registry = ProtectedTypesRegistry({User: 401})

        assert registry.get_status_code(Anonymous) is None
        assert registry.get_status_code(str) is None

    def test_error_detail_messages(self):
        """Error detail messages should be correct."""
        registry = ProtectedTypesRegistry({})

        assert registry.get_error_detail(401) == "Authentication required"
        assert registry.get_error_detail(403) == "Forbidden"
        assert registry.get_error_detail(500) == "Access denied"


# =============================================================================
# Public Route Tests (No Auth Type)
# =============================================================================


class TestPublicRoutes:
    """Test routes without auth types."""

    @pytest.mark.asyncio
    async def test_route_without_auth_type_works(self, base_container: Container, request_scope):
        """Routes without auth types should work normally."""
        auth_module = AuthModule()
        auth_module.configure(base_container)
        base_container.compile()

        executor = HandlerExecutor(base_container)

        async def handler():
            return {"status": "ok"}

        route = Route(
            path="/health",
            method=HTTPMethod.GET,
            handler=handler,
            name="health",
        )

        executor.compile_route(route)

        response = await executor.execute_route(route, make_mock_request(), {})

        assert response.status_code == 200
        body = json.loads(response.body.decode())
        assert body["status"] == "ok"
