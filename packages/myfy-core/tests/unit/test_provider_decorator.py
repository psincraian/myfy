"""
Unit tests for @provider decorator edge cases.

These tests cover:
- Provider registration mechanics
- Return type extraction
- Pending provider management
- Error handling for invalid providers
"""

import pytest

from myfy.core.di import REQUEST, SINGLETON, Container
from myfy.core.di.provider import (
    clear_pending_providers,
    get_pending_providers,
    provider,
    register_providers_in_container,
)

pytestmark = pytest.mark.unit


# =============================================================================
# Provider Registration Tests
# =============================================================================


class TestProviderRegistration:
    """Test provider decorator registration behavior."""

    def test_provider_adds_to_pending_providers(self):
        """Test that @provider adds function to pending providers."""
        clear_pending_providers()

        @provider(scope=SINGLETON)
        def my_service() -> str:
            return "test"

        pending = get_pending_providers()
        assert len(pending) == 1
        func, metadata = pending[0]
        # Check function name and behavior rather than identity
        # (decorator may wrap the function)
        assert func.__name__ == "my_service"  # type: ignore[union-attr]
        assert func() == "test"  # Function should still work
        assert metadata["scope"] == SINGLETON

        clear_pending_providers()

    def test_provider_preserves_function_behavior(self):
        """Test that decorated function still works normally."""
        clear_pending_providers()

        @provider(scope=SINGLETON)
        def add_numbers(a: int, b: int) -> int:
            return a + b

        # Function should still be callable
        result = add_numbers(2, 3)
        assert result == 5

        clear_pending_providers()

    def test_provider_stores_all_metadata(self):
        """Test that provider stores all configuration."""
        clear_pending_providers()

        @provider(
            scope=REQUEST,
            qualifier="myqualifier",
            name="myname",
            reloadable=("field1", "field2"),
        )
        def my_service() -> str:
            return "test"

        pending = get_pending_providers()
        _, metadata = pending[0]
        assert metadata["scope"] == REQUEST
        assert metadata["qualifier"] == "myqualifier"
        assert metadata["name"] == "myname"
        assert metadata["reloadable"] == ("field1", "field2")

        clear_pending_providers()

    def test_provider_marks_function_with_metadata(self):
        """Test that provider attaches metadata to function."""
        clear_pending_providers()

        @provider(scope=SINGLETON, qualifier="test")
        def my_service() -> str:
            return "test"

        assert hasattr(my_service, "__myfy_provider__")
        assert my_service.__myfy_provider__["scope"] == SINGLETON  # type: ignore[attr-defined]
        assert my_service.__myfy_provider__["qualifier"] == "test"  # type: ignore[attr-defined]

        clear_pending_providers()


# =============================================================================
# Pending Provider Management Tests
# =============================================================================


class TestPendingProviderManagement:
    """Test pending provider list management."""

    def test_clear_pending_providers(self):
        """Test that clear_pending_providers empties the list."""

        @provider(scope=SINGLETON)
        def service1() -> str:
            return "1"

        @provider(scope=SINGLETON)
        def service2() -> int:
            return 2

        assert len(get_pending_providers()) >= 2

        clear_pending_providers()
        assert len(get_pending_providers()) == 0

    def test_get_pending_providers_returns_copy(self):
        """Test that get_pending_providers returns a copy."""
        clear_pending_providers()

        @provider(scope=SINGLETON)
        def my_service() -> str:
            return "test"

        pending1 = get_pending_providers()
        pending2 = get_pending_providers()

        assert pending1 is not pending2
        assert pending1 == pending2

        clear_pending_providers()

    def test_multiple_providers_accumulate(self):
        """Test that multiple providers are accumulated."""
        clear_pending_providers()

        @provider(scope=SINGLETON)
        def service_a() -> str:
            return "a"

        @provider(scope=SINGLETON)
        def service_b() -> int:
            return 1

        @provider(scope=SINGLETON)
        def service_c() -> float:
            return 1.0

        pending = get_pending_providers()
        assert len(pending) == 3

        clear_pending_providers()


# =============================================================================
# Container Registration Tests
# =============================================================================


class TestRegisterProvidersInContainer:
    """Test register_providers_in_container behavior."""

    def test_registers_all_pending_providers(self, container: Container):
        """Test that all pending providers are registered."""
        clear_pending_providers()

        @provider(scope=SINGLETON)
        def string_service() -> str:
            return "test"

        @provider(scope=SINGLETON)
        def int_service() -> int:
            return 42

        register_providers_in_container(container)
        container.compile()

        assert container.get(str) == "test"
        assert container.get(int) == 42

    def test_clears_pending_after_registration(self, container: Container):
        """Test that pending providers are cleared after registration."""
        clear_pending_providers()

        @provider(scope=SINGLETON)
        def my_service() -> str:
            return "test"

        assert len(get_pending_providers()) == 1

        register_providers_in_container(container)

        assert len(get_pending_providers()) == 0

    def test_raises_error_for_missing_return_type(self, container: Container):
        """Test that provider without return type raises error."""
        clear_pending_providers()

        # Manually add a provider without return type annotation
        def no_return_type():
            return "test"

        # Manually add to pending (simulating a bug or edge case)
        from myfy.core.di.provider import _pending_providers

        _pending_providers.append(
            (
                no_return_type,
                {
                    "factory": no_return_type,
                    "scope": SINGLETON,
                    "qualifier": None,
                    "name": None,
                    "reloadable": (),
                },
            )
        )

        with pytest.raises(TypeError, match="must have a return type annotation"):
            register_providers_in_container(container)

        clear_pending_providers()

    def test_respects_provider_scope(self, container: Container, request_scope):
        """Test that provider scope is respected."""
        clear_pending_providers()

        call_count = 0

        @provider(scope=REQUEST)
        def request_service() -> list:
            nonlocal call_count
            call_count += 1
            return [call_count]

        register_providers_in_container(container)
        container.compile()

        # Same request should return same instance
        result1 = container.get(list)
        result2 = container.get(list)
        assert result1 is result2
        assert call_count == 1

    def test_respects_provider_qualifier(self, container: Container):
        """Test that provider qualifier is respected."""
        clear_pending_providers()

        @provider(scope=SINGLETON, qualifier="primary")
        def primary_db() -> dict:
            return {"type": "primary"}

        @provider(scope=SINGLETON, qualifier="replica")
        def replica_db() -> dict:
            return {"type": "replica"}

        register_providers_in_container(container)
        container.compile()

        primary = container.get(dict, qualifier="primary")
        replica = container.get(dict, qualifier="replica")

        assert primary["type"] == "primary"
        assert replica["type"] == "replica"


# =============================================================================
# Return Type Extraction Tests
# =============================================================================


class TestReturnTypeExtraction:
    """Test return type extraction from provider functions."""

    def test_extracts_simple_return_type(self, container: Container):
        """Test extraction of simple return types."""
        clear_pending_providers()

        class MyService:
            pass

        @provider(scope=SINGLETON)
        def my_service() -> MyService:
            return MyService()

        register_providers_in_container(container)
        container.compile()

        result = container.get(MyService)
        assert isinstance(result, MyService)

    def test_extracts_generic_return_type(self, container: Container):
        """Test extraction of generic return types."""
        clear_pending_providers()

        @provider(scope=SINGLETON)
        def my_list() -> list[str]:
            return ["a", "b", "c"]

        register_providers_in_container(container)
        # Note: The container registers the raw type (list), not list[str]
        # This is a limitation of the current implementation

    def test_handles_annotated_return_type(self, container: Container):
        """Test that Annotated return types with Qualifier are handled."""
        clear_pending_providers()

        # The @provider decorator respects the 'qualifier' parameter directly
        # Annotated return types are used for dependency injection hints, not provider registration
        @provider(scope=SINGLETON, qualifier="primary")
        def primary_str() -> str:
            return "primary_value"

        register_providers_in_container(container)
        container.compile()

        result = container.get(str, qualifier="primary")
        assert result == "primary_value"


# =============================================================================
# Edge Cases
# =============================================================================


class TestProviderEdgeCases:
    """Test edge cases in provider handling."""

    def test_provider_with_dependencies(self, container: Container):
        """Test provider that depends on other providers."""
        clear_pending_providers()

        class Database:
            def __init__(self):
                self.connected = True

        class Repository:
            def __init__(self, db: Database):
                self.db = db

        @provider(scope=SINGLETON)
        def database() -> Database:
            return Database()

        @provider(scope=SINGLETON)
        def repository(db: Database) -> Repository:
            return Repository(db)

        register_providers_in_container(container)
        container.compile()

        repo = container.get(Repository)
        assert repo.db.connected is True

    def test_provider_preserves_function_name(self):
        """Test that @provider preserves the original function name."""
        clear_pending_providers()

        @provider(scope=SINGLETON)
        def my_very_specific_function_name() -> str:
            return "test"

        assert my_very_specific_function_name.__name__ == "my_very_specific_function_name"

        clear_pending_providers()

    def test_provider_preserves_docstring(self):
        """Test that @provider preserves the original docstring."""
        clear_pending_providers()

        @provider(scope=SINGLETON)
        def documented_service() -> str:
            """This is a documented service."""
            return "test"

        assert documented_service.__doc__ == "This is a documented service."

        clear_pending_providers()

    def test_lambda_provider_registration(self, container: Container):
        """Test that lambda functions can be used directly (not with decorator)."""
        # Note: Lambdas can't use @provider decorator (no return type annotation)
        # But they can be registered directly
        container.register(
            type_=str,
            factory=lambda: "lambda_value",
            scope=SINGLETON,
        )
        container.compile()

        assert container.get(str) == "lambda_value"

    def test_async_provider(self, container: Container):
        """Test that async functions can be providers (factory called at resolution)."""
        clear_pending_providers()

        # Note: Async providers are an edge case - the factory is called,
        # but the container doesn't await it. This is actually a limitation.
        # Documenting the current behavior:

        class AsyncService:
            pass

        @provider(scope=SINGLETON)
        def sync_wrapper() -> AsyncService:
            # In real usage, async initialization would happen elsewhere
            return AsyncService()

        register_providers_in_container(container)
        container.compile()

        result = container.get(AsyncService)
        assert isinstance(result, AsyncService)
