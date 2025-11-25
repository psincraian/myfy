"""
Shared pytest fixtures for myfy-web tests.

This module provides:
- Container fixtures with web services
- Mock request factories
- Router fixtures
"""

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest

from myfy.core.config import CoreSettings
from myfy.core.di import SINGLETON, Container, ScopeContext
from myfy.core.di.provider import clear_pending_providers

# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


# =============================================================================
# Container Fixtures
# =============================================================================


@pytest.fixture
def container() -> Iterator[Container]:
    """
    Provide a fresh, uncompiled container for each test.

    This fixture ensures complete isolation between tests.
    """
    clear_pending_providers()
    c = Container()
    yield c
    clear_pending_providers()


@pytest.fixture
def compiled_container(container: Container) -> Container:
    """Provide a compiled container ready for resolution."""
    container.compile()
    return container


# =============================================================================
# Test Service Classes
# =============================================================================


class UserService:
    """Mock service for testing DI."""

    def get_user(self, user_id: int) -> dict:
        return {"id": user_id, "name": f"User {user_id}"}


# =============================================================================
# Web-Specific Container Fixtures
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


# =============================================================================
# Mock Request Factory
# =============================================================================


def make_mock_request(
    path_params: dict | None = None,
    body: bytes | None = None,
    method: str = "GET",
) -> MagicMock:
    """Create a mock Starlette request."""
    from starlette.requests import Request

    request = MagicMock(spec=Request)
    request.path_params = path_params or {}
    request.method = method

    async def get_body():
        return body or b""

    async def get_json():
        import json

        return json.loads(body.decode()) if body else {}

    request.body = get_body
    request.json = get_json

    return request


# =============================================================================
# Scope Context Fixtures
# =============================================================================


@pytest.fixture
def request_scope() -> Iterator[dict]:
    """Initialize and clean up a request scope for testing."""
    bag = ScopeContext.init_request_scope()
    yield bag
    ScopeContext.clear_request_bag()


# =============================================================================
# Cleanup Utilities
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_scopes():
    """Ensure scope contexts are cleaned up after each test."""
    yield
    try:
        ScopeContext.clear_request_bag()
    except Exception:
        pass
    try:
        ScopeContext.clear_task_bag()
    except Exception:
        pass
