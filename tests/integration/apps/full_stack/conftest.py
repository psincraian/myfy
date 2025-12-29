"""
Fixtures for full stack integration tests.

These tests require sqlalchemy, aiosqlite, and jinja2 to be installed.
"""

import pytest

# Skip all tests in this module if dependencies are not installed
pytest.importorskip("sqlalchemy", reason="sqlalchemy required for full_stack tests")
pytest.importorskip("aiosqlite", reason="aiosqlite required for full_stack tests")
pytest.importorskip("jinja2", reason="jinja2 required for full_stack tests")

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
def full_stack_app(tmp_path):
    """
    Create a fresh full stack application.

    Uses tmp_path for templates and in-memory SQLite for database.
    """
    app, router = create_app(tmp_path)
    app.initialize()
    return app


@pytest.fixture
def test_client(full_stack_app):
    """Create a test client with lifespan for full stack app."""
    web_module = full_stack_app.get_module(WebModule)

    # Create ASGI app with lifespan for DataModule startup
    lifespan = full_stack_app.create_lifespan()
    asgi_app = web_module.get_asgi_app(full_stack_app.container, lifespan=lifespan)

    with TestClient(asgi_app.app) as client:
        yield client
