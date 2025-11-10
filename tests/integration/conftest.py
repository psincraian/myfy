"""
Shared fixtures for integration tests.

Provides fixtures for full-stack testing with proper cleanup.
"""

import pytest

from myfy.core.di.provider import clear_pending_providers


@pytest.fixture(autouse=True)
def cleanup_providers():
    """
    Automatically clear provider registry before and after each integration test.

    Integration tests often use @provider decorators which can leak state.
    """
    clear_pending_providers()
    yield
    clear_pending_providers()


@pytest.fixture(autouse=True)
def cleanup_global_router():
    """Clean up global router state."""
    from myfy.web.routing import route

    route._routes.clear()
    yield
    route._routes.clear()
