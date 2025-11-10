"""
Tests for the provider decorator and registration system.

Tests the @provider decorator and automatic provider registration.
"""

from typing import Annotated

import pytest

from myfy.core.di.container import Container
from myfy.core.di.provider import (
    clear_pending_providers,
    get_pending_providers,
    provider,
    register_providers_in_container,
)
from myfy.core.di.scopes import SINGLETON, Scope
from myfy.core.di.types import Qualifier


class Database:
    def __init__(self, url: str = "default"):
        self.url = url


class Repository:
    def __init__(self, db: Database):
        self.db = db


class TestProviderDecorator:
    """Test the @provider decorator."""

    def setup_method(self):
        """Clear pending providers before each test."""
        clear_pending_providers()

    def test_provider_decorator_registers_pending_provider(self):
        """Should register provider in pending list."""

        @provider()
        def database() -> Database:
            return Database()

        pending = get_pending_providers()
        assert len(pending) == 1
        assert pending[0][1]["factory"] is database
        assert pending[0][1]["scope"] == SINGLETON

    def test_provider_decorator_with_custom_scope(self):
        """Should register provider with custom scope."""

        @provider(scope=Scope.REQUEST)
        def database() -> Database:
            return Database()

        pending = get_pending_providers()
        assert pending[0][1]["scope"] == Scope.REQUEST

    def test_provider_decorator_with_qualifier(self):
        """Should register provider with qualifier."""

        @provider(qualifier="primary")
        def database() -> Database:
            return Database("primary")

        pending = get_pending_providers()
        assert pending[0][1]["qualifier"] == "primary"

    def test_provider_decorator_with_name(self):
        """Should register provider with name."""

        @provider(name="main_db")
        def database() -> Database:
            return Database()

        pending = get_pending_providers()
        assert pending[0][1]["name"] == "main_db"

    def test_provider_decorator_preserves_function(self):
        """Should preserve original function behavior."""

        @provider()
        def database() -> Database:
            return Database("test")

        # Function should still be callable
        db = database()
        assert isinstance(db, Database)
        assert db.url == "test"

    def test_provider_decorator_adds_metadata(self):
        """Should add metadata to function."""

        @provider(scope=Scope.REQUEST, qualifier="test")
        def database() -> Database:
            return Database()

        assert hasattr(database, "__myfy_provider__")
        metadata = database.__myfy_provider__  # type: ignore
        assert metadata["scope"] == Scope.REQUEST
        assert metadata["qualifier"] == "test"

    def test_multiple_providers(self):
        """Should register multiple providers."""

        @provider()
        def database() -> Database:
            return Database()

        @provider()
        def repository(db: Database) -> Repository:
            return Repository(db)

        pending = get_pending_providers()
        assert len(pending) == 2


class TestRegisterProvidersInContainer:
    """Test automatic provider registration in container."""

    def setup_method(self):
        """Clear pending providers before each test."""
        clear_pending_providers()

    def test_register_providers_in_container(self):
        """Should register all pending providers in container."""

        @provider()
        def database() -> Database:
            return Database()

        @provider()
        def repository(db: Database) -> Repository:
            return Repository(db)

        container = Container()
        register_providers_in_container(container)

        assert len(container._providers) == 2

    def test_register_providers_clears_pending_list(self):
        """Should clear pending list after registration."""

        @provider()
        def database() -> Database:
            return Database()

        container = Container()
        register_providers_in_container(container)

        # Pending list should be cleared
        pending = get_pending_providers()
        assert len(pending) == 0

    def test_register_provider_without_return_type_raises_error(self):
        """Should raise error for provider without return type."""

        @provider()
        def database():  # Missing return type
            return Database()

        container = Container()

        with pytest.raises(TypeError, match="must have a return type annotation"):
            register_providers_in_container(container)

    def test_register_provider_with_annotated_return_type(self):
        """Should handle Annotated return types."""

        @provider(qualifier="primary")
        def database() -> Annotated[Database, Qualifier("primary")]:
            return Database("primary")

        container = Container()
        register_providers_in_container(container)

        # Should extract actual type and qualifier
        assert len(container._providers) == 1

    def test_register_providers_with_different_scopes(self):
        """Should register providers with different scopes."""

        @provider(scope=SINGLETON)
        def singleton_db() -> Database:
            return Database()

        class RequestService:
            pass

        @provider(scope=Scope.REQUEST)
        def request_service() -> RequestService:
            return RequestService()

        container = Container()
        register_providers_in_container(container)

        # Verify scopes
        db_key = next(k for k in container._providers if k.type == Database)
        svc_key = next(k for k in container._providers if k.type == RequestService)

        assert container._providers[db_key].scope == SINGLETON
        assert container._providers[svc_key].scope == Scope.REQUEST

    def test_register_providers_with_qualifiers(self):
        """Should register multiple providers with qualifiers."""

        @provider(qualifier="primary")
        def primary_db() -> Database:
            return Database("primary")

        @provider(qualifier="secondary")
        def secondary_db() -> Database:
            return Database("secondary")

        container = Container()
        register_providers_in_container(container)

        assert len(container._providers) == 2

        # Verify both registered
        primary_key = next(k for k in container._providers if k.qualifier == "primary")
        secondary_key = next(k for k in container._providers if k.qualifier == "secondary")

        assert primary_key.type == Database
        assert secondary_key.type == Database


class TestProviderIntegration:
    """Test provider decorator integrated with container."""

    def setup_method(self):
        """Clear pending providers before each test."""
        clear_pending_providers()

    def test_full_provider_workflow(self):
        """Should work end-to-end: decorate -> register -> compile -> resolve."""

        @provider()
        def database() -> Database:
            return Database("test-db")

        @provider()
        def repository(db: Database) -> Repository:
            return Repository(db)

        # Register and compile
        container = Container()
        register_providers_in_container(container)
        container.compile()

        # Resolve
        repo = container.get(Repository)
        assert isinstance(repo, Repository)
        assert repo.db.url == "test-db"

    def test_provider_with_dependencies_and_qualifiers(self):
        """Should resolve provider with qualified dependencies."""

        @provider(qualifier="primary")
        def primary_db() -> Database:
            return Database("primary")

        @provider(qualifier="secondary")
        def secondary_db() -> Database:
            return Database("secondary")

        @provider()
        def repository(db: Annotated[Database, Qualifier("primary")]) -> Repository:
            return Repository(db)

        container = Container()
        register_providers_in_container(container)
        container.compile()

        repo = container.get(Repository)
        assert repo.db.url == "primary"

    def test_provider_request_scoped(self):
        """Should work with request-scoped providers."""
        from myfy.core.di.scopes import ScopeContext

        class RequestService:
            pass

        @provider(scope=Scope.REQUEST)
        def request_service() -> RequestService:
            return RequestService()

        container = Container()
        register_providers_in_container(container)
        container.compile()

        # Resolve within request context
        with ScopeContext.request():
            svc1 = container.get(RequestService)
            svc2 = container.get(RequestService)
            assert svc1 is svc2  # Same instance within request

    def test_clear_pending_providers(self):
        """Should clear pending providers list."""

        @provider()
        def database() -> Database:
            return Database()

        assert len(get_pending_providers()) == 1

        clear_pending_providers()

        assert len(get_pending_providers()) == 0
