"""Fixtures for web+data integration tests."""

import pytest
from starlette.testclient import TestClient

from myfy.core.di import ScopeContext
from myfy.core.di.provider import clear_pending_providers
from myfy.web import WebModule

from .app import create_app


@pytest.fixture(autouse=True)
def clean_providers():
    """Ensure providers are cleaned between tests."""
    clear_pending_providers()
    yield
    clear_pending_providers()


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


@pytest.fixture
def web_data_app():
    """
    Create a fresh web+data application with in-memory SQLite.

    Each test gets a fresh database.
    """
    # Use in-memory SQLite for fast, isolated tests
    app, router = create_app(database_url="sqlite+aiosqlite:///:memory:")
    app.initialize()
    return app


@pytest.fixture
def test_client(web_data_app):
    """Create a test client with lifespan for database initialization."""
    web_module = web_data_app.get_module(WebModule)

    # Create ASGI app with lifespan to trigger DataModule.start()
    # which creates the database tables
    lifespan = web_data_app.create_lifespan()
    asgi_app = web_module.get_asgi_app(web_data_app.container, lifespan=lifespan)

    # TestClient handles lifespan automatically
    with TestClient(asgi_app.app) as client:
        yield client
