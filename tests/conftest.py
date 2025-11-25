"""
Shared pytest fixtures for end-to-end tests.

This module provides:
- E2E application fixtures
- Provider cleanup utilities
"""

import asyncio

import pytest

from myfy.core.di import ScopeContext
from myfy.core.di.provider import clear_pending_providers

# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


# =============================================================================
# Event Loop Configuration
# =============================================================================


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default event loop policy."""
    return asyncio.DefaultEventLoopPolicy()


# =============================================================================
# Provider Cleanup
# =============================================================================


@pytest.fixture(autouse=True)
def clean_providers():
    """Ensure providers are cleaned between tests."""
    clear_pending_providers()
    yield
    clear_pending_providers()


# =============================================================================
# Scope Cleanup
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
