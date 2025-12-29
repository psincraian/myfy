"""
Fixtures for web+frontend integration tests.
"""

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
def web_frontend_app(tmp_path):
    """
    Create a fresh web+frontend application.

    Uses tmp_path for templates and static files.
    """
    app, router, templates_dir, static_dir = create_app(tmp_path)
    app.initialize()
    return app, templates_dir, static_dir


@pytest.fixture
def test_client(web_frontend_app):
    """Create a test client for the web+frontend application."""
    app, templates_dir, static_dir = web_frontend_app
    web_module = app.get_module(WebModule)
    asgi_app = web_module.get_asgi_app(app.container)
    return TestClient(asgi_app.app)
