"""
Shared test fixtures for myfy-core tests.

Provides reusable fixtures to avoid code duplication and ensure test isolation.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from myfy.core.di.container import Container
from myfy.core.di.provider import clear_pending_providers
from myfy.core.di.scopes import ScopeContext as _ScopeContext


# Test helpers for scope contexts
class ScopeContext:
    """Test helper that provides context managers for request and task scopes."""

    @staticmethod
    @contextmanager
    def request() -> Iterator[dict]:
        """Context manager for request scope in tests."""
        bag = _ScopeContext.init_request_scope()
        try:
            yield bag
        finally:
            _ScopeContext.clear_request_bag()

    @staticmethod
    @contextmanager
    def task() -> Iterator[dict]:
        """Context manager for task scope in tests."""
        bag = _ScopeContext.init_task_scope()
        try:
            yield bag
        finally:
            _ScopeContext.clear_task_bag()


# Test models
class Database:
    """Mock database for testing."""

    def __init__(self, url: str = "default"):
        self.url = url


class Repository:
    """Mock repository for testing."""

    def __init__(self, db: Database):
        self.db = db


class Service:
    """Mock service for testing."""

    def __init__(self, repo: Repository):
        self.repo = repo


# Fixtures
@pytest.fixture
def container():
    """Provide a clean DI container for each test."""
    return Container()


@pytest.fixture
def compiled_container():
    """Provide a compiled DI container for each test."""
    container = Container()
    container.compile()
    return container


@pytest.fixture
def container_factory():
    """Factory for creating containers with custom providers."""

    def _factory(providers: dict):
        """
        Create and compile a container with the given providers.

        Args:
            providers: Dict mapping types to factory functions

        Returns:
            Compiled Container instance
        """
        from myfy.core.di.scopes import SINGLETON

        container = Container()
        for type_, factory in providers.items():
            scope = getattr(factory, "_scope", SINGLETON)
            container.register(type_, factory, scope=scope)
        container.compile()
        return container

    return _factory


@pytest.fixture(autouse=True)
def clear_provider_registry():
    """
    Automatically clear provider registry before and after each test.

    This prevents test pollution from @provider decorators.
    """
    clear_pending_providers()
    yield
    clear_pending_providers()


@pytest.fixture
def database():
    """Provide a test database instance."""
    return Database("test-db")


@pytest.fixture
def repository(database):
    """Provide a test repository with database."""
    return Repository(database)


@pytest.fixture
def service(repository):
    """Provide a test service with repository."""
    return Service(repository)
