"""
Shared test fixtures for myfy-web tests.

Provides reusable fixtures for web testing with proper isolation.
"""

import pytest
from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.testclient import TestClient

from myfy.core.di.container import Container
from myfy.web.routing import Router


class User(BaseModel):
    """Test user model."""

    name: str
    email: str


class Database:
    """Mock database service."""

    def __init__(self):
        self.connected = True


# Fixtures
@pytest.fixture
def container():
    """Provide a clean DI container."""
    container = Container()
    container.compile()
    return container


@pytest.fixture
def router():
    """Provide a clean router instance for each test."""
    return Router()


@pytest.fixture(autouse=True)
def reset_global_router():
    """
    Reset global router state before and after each test.

    This prevents test pollution from the global 'route' instance.
    """
    from myfy.web.routing import route

    # Clear routes before test
    route._routes.clear()
    yield
    # Clear routes after test
    route._routes.clear()


@pytest.fixture
def test_request():
    """Factory for creating test requests."""

    def _factory(method: str = "GET", path: str = "/test", headers: dict | None = None):
        """Create a Starlette Request for testing."""
        app = Starlette()
        client = TestClient(app)

        header_list = []
        if headers:
            header_list = [(k.encode(), v.encode()) for k, v in headers.items()]

        return Request({"type": "http", "method": method, "path": path, "headers": header_list}, client)

    return _factory


@pytest.fixture
def database():
    """Provide a test database instance."""
    return Database()
