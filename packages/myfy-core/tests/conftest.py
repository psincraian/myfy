"""
Shared pytest fixtures for myfy-core tests.

This module provides:
- Isolated containers for each test
- Mock modules and services
- Scope context fixtures
"""

import asyncio
from collections.abc import Iterator
from typing import Any

import pytest

from myfy.core.di import REQUEST, SINGLETON, TASK, Container, ScopeContext
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
# Event Loop Configuration
# =============================================================================


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default event loop policy."""
    return asyncio.DefaultEventLoopPolicy()


# =============================================================================
# Container Fixtures
# =============================================================================


@pytest.fixture
def container() -> Iterator[Container]:
    """
    Provide a fresh, uncompiled container for each test.

    This fixture ensures complete isolation between tests.
    """
    # Clear any pending providers from previous tests
    clear_pending_providers()

    c = Container()
    yield c

    # Cleanup: clear pending providers after test
    clear_pending_providers()


@pytest.fixture
def compiled_container(container: Container) -> Container:
    """
    Provide a compiled container ready for resolution.

    Use this when you need to test resolution behavior.
    """
    container.compile()
    return container


# =============================================================================
# Scope Context Fixtures
# =============================================================================


@pytest.fixture
def request_scope() -> Iterator[dict[str, Any]]:
    """
    Initialize and clean up a request scope for testing.

    Use this when testing request-scoped dependencies.
    """
    bag = ScopeContext.init_request_scope()
    yield bag
    ScopeContext.clear_request_bag()


@pytest.fixture
def task_scope() -> Iterator[dict[str, Any]]:
    """
    Initialize and clean up a task scope for testing.

    Use this when testing task-scoped dependencies.
    """
    bag = ScopeContext.init_task_scope()
    yield bag
    ScopeContext.clear_task_bag()


# =============================================================================
# Test Service Classes
# =============================================================================


class SimpleService:
    """A simple test service with no dependencies."""

    def __init__(self, value: str = "default"):
        self.value = value

    def get_value(self) -> str:
        return self.value


class DependentService:
    """A test service that depends on SimpleService."""

    def __init__(self, simple: SimpleService):
        self.simple = simple

    def get_combined(self) -> str:
        return f"combined:{self.simple.get_value()}"


class CountingService:
    """A service that tracks how many times it's been instantiated."""

    _instance_count = 0

    def __init__(self):
        CountingService._instance_count += 1
        self.instance_id = CountingService._instance_count

    @classmethod
    def reset_count(cls):
        cls._instance_count = 0


class AsyncService:
    """A service that provides async operations."""

    def __init__(self):
        self.initialized = False

    async def initialize(self):
        await asyncio.sleep(0)  # Simulate async operation
        self.initialized = True

    async def do_work(self) -> str:
        return "async_work_done"


# =============================================================================
# Container Factory Fixtures
# =============================================================================


@pytest.fixture
def container_with_simple_service(container: Container) -> Container:
    """Container with a simple singleton service registered."""
    container.register(
        type_=SimpleService,
        factory=lambda: SimpleService("test_value"),
        scope=SINGLETON,
    )
    return container


@pytest.fixture
def container_with_dependency_chain(container: Container) -> Container:
    """Container with a dependency chain: DependentService -> SimpleService."""
    container.register(
        type_=SimpleService,
        factory=lambda: SimpleService("base"),
        scope=SINGLETON,
    )
    container.register(
        type_=DependentService,
        factory=lambda simple: DependentService(simple),
        scope=SINGLETON,
    )
    return container


@pytest.fixture
def container_with_all_scopes(container: Container) -> Container:
    """Container with services in all scopes."""
    # Reset counting service
    CountingService.reset_count()

    container.register(
        type_=str,
        factory=lambda: "singleton_value",
        scope=SINGLETON,
        qualifier="singleton",
    )
    container.register(
        type_=str,
        factory=lambda: "request_value",
        scope=REQUEST,
        qualifier="request",
    )
    container.register(
        type_=str,
        factory=lambda: "task_value",
        scope=TASK,
        qualifier="task",
    )
    return container


# =============================================================================
# Mock Module Fixtures
# =============================================================================


class MockModule:
    """A configurable mock module for testing."""

    def __init__(
        self,
        name: str = "mock",
        requires: list[type] | None = None,
        provides: list[type] | None = None,
        configure_fn: Any = None,
        extend_fn: Any = None,
        finalize_fn: Any = None,
    ):
        self._name = name
        self._requires = requires or []
        self._provides = provides or []
        self._configure_fn = configure_fn
        self._extend_fn = extend_fn
        self._finalize_fn = finalize_fn

        # Tracking
        self.configure_called = False
        self.extend_called = False
        self.finalize_called = False
        self.start_called = False
        self.stop_called = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def requires(self) -> list[type]:
        return self._requires

    @property
    def provides(self) -> list[type]:
        return self._provides

    def configure(self, container: Container) -> None:
        self.configure_called = True
        if self._configure_fn:
            self._configure_fn(container)

    def extend(self, container: Container) -> None:
        self.extend_called = True
        if self._extend_fn:
            self._extend_fn(container)

    def finalize(self, container: Container) -> None:
        self.finalize_called = True
        if self._finalize_fn:
            self._finalize_fn(container)

    async def start(self) -> None:
        self.start_called = True

    async def stop(self) -> None:
        self.stop_called = True


@pytest.fixture
def mock_module_factory():
    """Factory for creating mock modules with custom behavior."""

    def factory(**kwargs) -> MockModule:
        return MockModule(**kwargs)

    return factory


# =============================================================================
# Async Test Utilities
# =============================================================================


@pytest.fixture
async def async_service() -> AsyncService:
    """Provide an initialized async service."""
    service = AsyncService()
    await service.initialize()
    return service


# =============================================================================
# Cleanup Utilities
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_scopes():
    """Ensure scope contexts are cleaned up after each test."""
    yield
    # Clear any leftover scope bags
    try:
        ScopeContext.clear_request_bag()
    except Exception:
        pass
    try:
        ScopeContext.clear_task_bag()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def reset_counting_service():
    """Reset the counting service counter after each test."""
    yield
    CountingService.reset_count()
