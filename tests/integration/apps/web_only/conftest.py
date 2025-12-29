"""
Fixtures for web-only integration tests.
"""

import pytest
from starlette.testclient import TestClient

from myfy.core.di.provider import clear_pending_providers
from myfy.web import WebModule

from .app import create_app


@pytest.fixture(autouse=True)
def clean_providers():
    """Ensure providers are cleaned between tests."""
    clear_pending_providers()
    yield
    clear_pending_providers()


@pytest.fixture
def web_only_app():
    """Create a fresh web-only application for each test."""
    app, router = create_app()
    app.initialize()
    return app


@pytest.fixture
def test_client(web_only_app):
    """Create a test client for the web-only application."""
    web_module = web_only_app.get_module(WebModule)
    asgi_app = web_module.get_asgi_app(web_only_app.container)
    return TestClient(asgi_app.app)
