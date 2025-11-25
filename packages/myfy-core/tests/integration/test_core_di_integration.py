"""
Integration tests for myfy-core DI system.

These tests verify that all DI components work together:
- Container with all scope types
- Provider decorator integration
- Dependency resolution chains
- Override mechanism
"""

from typing import Annotated

import pytest

from myfy.core.di import (
    REQUEST,
    SINGLETON,
    Container,
    ScopeContext,
)
from myfy.core.di.provider import (
    clear_pending_providers,
    provider,
    register_providers_in_container,
)
from myfy.core.di.types import Qualifier

pytestmark = pytest.mark.integration


# =============================================================================
# Test Services
# =============================================================================


class DatabaseConfig:
    """Configuration for database connection."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def connection_string(self) -> str:
        return f"db://{self.host}:{self.port}"


class Database:
    """Simulated database connection."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connected = False

    def connect(self) -> None:
        self.connected = True

    def query(self, sql: str) -> list[dict]:
        return [{"result": sql}]


class UserRepository:
    """Repository for user operations."""

    def __init__(self, db: Database):
        self.db = db

    def get_user(self, user_id: int) -> dict:
        return {"id": user_id, "db": self.db.config.connection_string()}


class UserService:
    """Business logic for users."""

    def __init__(self, repo: UserRepository):
        self.repo = repo

    def find_user(self, user_id: int) -> dict:
        return self.repo.get_user(user_id)


class RequestLogger:
    """Request-scoped logger."""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self.logs: list[str] = []

    def log(self, message: str) -> None:
        self.logs.append(f"[{self.request_id}] {message}")


# =============================================================================
# Full Dependency Chain Tests
# =============================================================================


class TestFullDependencyChain:
    """Test complete dependency resolution chains."""

    def test_four_level_dependency_chain(self, container: Container):
        """Test Config -> Database -> Repository -> Service chain."""

        # Define typed factory functions for proper dependency resolution
        def config_factory() -> DatabaseConfig:
            return DatabaseConfig("localhost", 5432)

        def db_factory(config: DatabaseConfig) -> Database:
            return Database(config)

        def repo_factory(db: Database) -> UserRepository:
            return UserRepository(db)

        def service_factory(repo: UserRepository) -> UserService:
            return UserService(repo)

        container.register(type_=DatabaseConfig, factory=config_factory, scope=SINGLETON)
        container.register(type_=Database, factory=db_factory, scope=SINGLETON)
        container.register(type_=UserRepository, factory=repo_factory, scope=SINGLETON)
        container.register(type_=UserService, factory=service_factory, scope=SINGLETON)
        container.compile()

        # Resolve the top-level service
        service = container.get(UserService)

        # Verify the entire chain is connected
        user = service.find_user(123)
        assert user["id"] == 123
        assert "localhost:5432" in user["db"]

    def test_shared_dependencies(self, container: Container):
        """Test that shared dependencies are the same instance."""

        def config_factory() -> DatabaseConfig:
            return DatabaseConfig("shared", 5432)

        def db_factory(config: DatabaseConfig) -> Database:
            return Database(config)

        container.register(type_=DatabaseConfig, factory=config_factory, scope=SINGLETON)
        container.register(type_=Database, factory=db_factory, scope=SINGLETON)

        # Two services that both depend on Database
        class ServiceA:
            def __init__(self, db: Database):
                self.db = db

        class ServiceB:
            def __init__(self, db: Database):
                self.db = db

        def service_a_factory(db: Database) -> ServiceA:
            return ServiceA(db)

        def service_b_factory(db: Database) -> ServiceB:
            return ServiceB(db)

        container.register(type_=ServiceA, factory=service_a_factory, scope=SINGLETON)
        container.register(type_=ServiceB, factory=service_b_factory, scope=SINGLETON)
        container.compile()

        service_a = container.get(ServiceA)
        service_b = container.get(ServiceB)

        # Both should have the same Database instance
        assert service_a.db is service_b.db


# =============================================================================
# Provider Decorator Integration Tests
# =============================================================================


class TestProviderDecoratorIntegration:
    """Test @provider decorator with container."""

    def test_decorator_and_manual_registration_together(self, container: Container):
        """Test that @provider and manual registration work together."""
        clear_pending_providers()

        # Manual registration
        container.register(
            type_=str,
            factory=lambda: "manual",
            scope=SINGLETON,
            qualifier="manual",
        )

        # Decorator registration
        @provider(scope=SINGLETON, qualifier="decorated")
        def decorated_str() -> str:
            return "decorated"

        register_providers_in_container(container)
        container.compile()

        assert container.get(str, qualifier="manual") == "manual"
        assert container.get(str, qualifier="decorated") == "decorated"

        clear_pending_providers()

    def test_provider_dependency_on_manual_registration(self, container: Container):
        """Test @provider depending on manually registered service."""
        clear_pending_providers()

        container.register(
            type_=DatabaseConfig,
            factory=lambda: DatabaseConfig("test", 5432),
            scope=SINGLETON,
        )

        @provider(scope=SINGLETON)
        def database(config: DatabaseConfig) -> Database:
            return Database(config)

        register_providers_in_container(container)
        container.compile()

        db = container.get(Database)
        assert db.config.host == "test"

        clear_pending_providers()


# =============================================================================
# Mixed Scope Integration Tests
# =============================================================================


class TestMixedScopeIntegration:
    """Test integration of different scopes."""

    def test_request_scoped_depends_on_singleton(self, container: Container, request_scope):
        """Test request-scoped service depending on singleton."""
        request_id_counter = [0]

        def config_factory() -> DatabaseConfig:
            return DatabaseConfig("singleton", 5432)

        def db_factory(config: DatabaseConfig) -> Database:
            return Database(config)

        def create_request_logger() -> RequestLogger:
            request_id_counter[0] += 1
            return RequestLogger(f"req-{request_id_counter[0]}")

        container.register(
            type_=DatabaseConfig,
            factory=config_factory,
            scope=SINGLETON,
        )
        container.register(
            type_=Database,
            factory=db_factory,
            scope=SINGLETON,
        )
        container.register(
            type_=RequestLogger,
            factory=create_request_logger,
            scope=REQUEST,
        )

        # Service that uses both
        class RequestHandler:
            def __init__(self, db: Database, logger: RequestLogger):
                self.db = db
                self.logger = logger

        def handler_factory(db: Database, logger: RequestLogger) -> RequestHandler:
            return RequestHandler(db, logger)

        container.register(
            type_=RequestHandler,
            factory=handler_factory,
            scope=REQUEST,
        )
        container.compile()

        handler = container.get(RequestHandler)

        # Verify singleton is shared
        assert handler.db.config.host == "singleton"
        # Verify request-scoped is unique per request
        assert handler.logger.request_id == "req-1"

    def test_multiple_requests_get_different_instances(self, container: Container):
        """Test that different requests get different request-scoped instances."""
        request_counter = [0]

        container.register(
            type_=DatabaseConfig,
            factory=lambda: DatabaseConfig("shared", 5432),
            scope=SINGLETON,
        )

        def create_logger():
            request_counter[0] += 1
            return RequestLogger(f"req-{request_counter[0]}")

        container.register(
            type_=RequestLogger,
            factory=create_logger,
            scope=REQUEST,
        )
        container.compile()

        # Simulate first request
        ScopeContext.init_request_scope()
        logger1 = container.get(RequestLogger)
        logger1_again = container.get(RequestLogger)
        ScopeContext.clear_request_bag()

        # Simulate second request
        ScopeContext.init_request_scope()
        logger2 = container.get(RequestLogger)
        ScopeContext.clear_request_bag()

        # Within same request, same instance
        assert logger1 is logger1_again
        # Across requests, different instances
        assert logger1 is not logger2
        assert logger1.request_id == "req-1"
        assert logger2.request_id == "req-2"


# =============================================================================
# Override Integration Tests
# =============================================================================


class TestOverrideIntegration:
    """Test override mechanism with real dependencies."""

    def test_override_in_dependency_chain(self, container: Container):
        """Test overriding a dependency in the middle of a chain."""

        def config_factory() -> DatabaseConfig:
            return DatabaseConfig("production", 5432)

        def db_factory(config: DatabaseConfig) -> Database:
            return Database(config)

        def repo_factory(db: Database) -> UserRepository:
            return UserRepository(db)

        container.register(type_=DatabaseConfig, factory=config_factory, scope=SINGLETON)
        container.register(type_=Database, factory=db_factory, scope=SINGLETON)
        container.register(type_=UserRepository, factory=repo_factory, scope=SINGLETON)
        container.compile()

        # Normal resolution
        repo = container.get(UserRepository)
        assert repo.db.config.host == "production"

        # Override the Database
        class FakeDatabase:
            def __init__(self):
                self.config = DatabaseConfig("fake", 0)

        with container.override({Database: lambda: FakeDatabase()}):
            # UserRepository still comes from container
            # But Database is now faked
            fake_db = container.get(Database)
            assert fake_db.config.host == "fake"

        # Back to normal
        real_db = container.get(Database)
        assert real_db.config.host == "production"

    def test_override_does_not_affect_cached_singletons(self, container: Container):
        """Test that override doesn't modify already-cached singletons."""
        container.register(
            type_=DatabaseConfig,
            factory=lambda: DatabaseConfig("original", 5432),
            scope=SINGLETON,
        )
        container.compile()

        # Resolve to cache the singleton
        original = container.get(DatabaseConfig)
        assert original.host == "original"

        # Override
        with container.override({DatabaseConfig: lambda: DatabaseConfig("override", 0)}):
            # Gets the override, not the cached original
            overridden = container.get(DatabaseConfig)
            assert overridden.host == "override"

        # After override, back to cached original
        after = container.get(DatabaseConfig)
        assert after is original


# =============================================================================
# Qualifier Integration Tests
# =============================================================================


class TestQualifierIntegration:
    """Test qualifier-based resolution integration."""

    def test_multiple_databases_with_qualifiers(self, container: Container):
        """Test multiple database connections with qualifiers."""
        container.register(
            type_=Database,
            factory=lambda: Database(DatabaseConfig("primary", 5432)),
            scope=SINGLETON,
            qualifier="primary",
        )
        container.register(
            type_=Database,
            factory=lambda: Database(DatabaseConfig("replica", 5433)),
            scope=SINGLETON,
            qualifier="replica",
        )
        container.compile()

        primary = container.get(Database, qualifier="primary")
        replica = container.get(Database, qualifier="replica")

        assert primary.config.host == "primary"
        assert replica.config.host == "replica"
        assert primary is not replica

    def test_annotated_qualifier_in_dependency(self, container: Container):
        """Test using Annotated[T, Qualifier] for dependency injection."""
        clear_pending_providers()

        container.register(
            type_=str,
            factory=lambda: "primary_connection",
            scope=SINGLETON,
            qualifier="primary",
        )
        container.register(
            type_=str,
            factory=lambda: "replica_connection",
            scope=SINGLETON,
            qualifier="replica",
        )

        # Service that uses qualified dependencies
        class MultiDbService:
            def __init__(
                self,
                primary: Annotated[str, Qualifier("primary")],
                replica: Annotated[str, Qualifier("replica")],
            ):
                self.primary = primary
                self.replica = replica

        container.register(
            type_=MultiDbService,
            factory=lambda primary, replica: MultiDbService(primary, replica),
            scope=SINGLETON,
        )

        # Manually set up the qualified dependencies
        from myfy.core.di.types import ProviderKey

        service_reg = container._providers[ProviderKey(MultiDbService)]
        service_reg.dependencies = [
            ProviderKey(str, "primary"),
            ProviderKey(str, "replica"),
        ]

        container.compile()

        service = container.get(MultiDbService)
        assert service.primary == "primary_connection"
        assert service.replica == "replica_connection"


# =============================================================================
# Error Recovery Tests
# =============================================================================


class TestErrorRecoveryIntegration:
    """Test error handling and recovery in integrated scenarios."""

    def test_factory_exception_does_not_corrupt_container(self, container: Container):
        """Test that factory exceptions don't corrupt container state."""
        call_count = [0]

        def failing_factory():
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("First call fails")
            return "success"

        container.register(
            type_=str,
            factory=failing_factory,
            scope=SINGLETON,
        )
        container.compile()

        # First call fails
        with pytest.raises(ValueError, match="First call fails"):
            container.get(str)

        # Second call should succeed (factory is retried for singletons that failed)
        result = container.get(str)
        assert result == "success"

    def test_scope_cleanup_after_exception(self, container: Container, request_scope):
        """Test that scope is properly cleaned even after exceptions."""
        container.register(
            type_=RequestLogger,
            factory=lambda: RequestLogger("test"),
            scope=REQUEST,
        )
        container.compile()

        # Get a request-scoped service
        logger = container.get(RequestLogger)
        logger.log("before exception")

        # Simulate an exception in user code
        try:
            raise RuntimeError("Simulated error")
        except RuntimeError:
            pass

        # Scope should still be valid
        same_logger = container.get(RequestLogger)
        assert same_logger is logger
        assert len(logger.logs) == 1
