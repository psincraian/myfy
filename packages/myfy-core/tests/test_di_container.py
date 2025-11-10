"""
Tests for the dependency injection container.

Tests ADR-0003: Dependency Injection Container with compile-time resolution.
"""

import threading
from typing import Annotated

import pytest

from myfy.core.di.container import Container
from myfy.core.di.errors import (
    CircularDependencyError,
    ContainerFrozenError,
    DIError,
    DuplicateProviderError,
    ProviderNotFoundError,
    ScopeMismatchError,
)
from myfy.core.di.scopes import SINGLETON, Scope, ScopeContext
from myfy.core.di.types import Qualifier


# Test fixtures and mock classes
class Database:
    def __init__(self, url: str = "default"):
        self.url = url


class Repository:
    def __init__(self, db: Database):
        self.db = db


class Service:
    def __init__(self, repo: Repository):
        self.repo = repo


class RequestScopedService:
    def __init__(self):
        pass


class TaskScopedService:
    def __init__(self):
        pass


class TestContainerRegistration:
    """Test provider registration in the container."""

    def test_register_provider(self):
        """Should register a provider successfully."""
        container = Container()

        def db_factory() -> Database:
            return Database()

        container.register(Database, db_factory, scope=SINGLETON)

        assert len(container._providers) == 1

    def test_register_duplicate_provider_raises_error(self):
        """Should raise error when registering duplicate provider."""
        container = Container()

        def db_factory() -> Database:
            return Database()

        container.register(Database, db_factory)

        with pytest.raises(DuplicateProviderError):
            container.register(Database, db_factory)

    def test_register_with_qualifier(self):
        """Should register multiple providers with qualifiers."""
        container = Container()

        def primary_db() -> Database:
            return Database("primary")

        def secondary_db() -> Database:
            return Database("secondary")

        container.register(Database, primary_db, qualifier="primary")
        container.register(Database, secondary_db, qualifier="secondary")

        assert len(container._providers) == 2

    def test_register_after_compile_raises_error(self):
        """Should raise error when registering after compilation."""
        container = Container()

        def db_factory() -> Database:
            return Database()

        container.register(Database, db_factory)
        container.compile()

        def repo_factory() -> Repository:
            return Repository(Database())

        with pytest.raises(ContainerFrozenError):
            container.register(Repository, repo_factory)


class TestContainerCompilation:
    """Test container compilation and dependency analysis."""

    def test_compile_analyzes_dependencies(self):
        """Should analyze dependencies during compilation."""
        container = Container()

        def db_factory() -> Database:
            return Database()

        def repo_factory(db: Database) -> Repository:
            return Repository(db)

        container.register(Database, db_factory)
        container.register(Repository, repo_factory)

        container.compile()

        container._providers[container._providers.keys().__iter__().__next__()]
        # At least one provider should have dependencies
        assert any(reg.dependencies for reg in container._providers.values())

    def test_compile_detects_circular_dependencies(self):
        """Should detect circular dependencies during compilation."""
        container = Container()

        class A:
            pass

        class B:
            pass

        def a_factory(b: B) -> A:
            return A()

        def b_factory(a: A) -> B:
            return B()

        container.register(A, a_factory)
        container.register(B, b_factory)

        with pytest.raises(CircularDependencyError):
            container.compile()

    def test_compile_detects_self_circular_dependency(self):
        """Should detect self-referencing circular dependencies."""
        container = Container()

        class A:
            pass

        def a_factory(a: A) -> A:
            return A()

        container.register(A, a_factory)

        with pytest.raises(CircularDependencyError):
            container.compile()

    def test_compile_validates_scope_mismatch(self):
        """Should detect singleton depending on request-scoped dependency."""
        container = Container()

        def request_service() -> RequestScopedService:
            return RequestScopedService()

        def singleton_service(req_svc: RequestScopedService) -> Service:
            return Service(Repository(Database()))

        container.register(RequestScopedService, request_service, scope=Scope.REQUEST)
        container.register(Service, singleton_service, scope=SINGLETON)

        with pytest.raises(ScopeMismatchError):
            container.compile()

    def test_compile_builds_injection_plan(self):
        """Should build injection plans for all providers."""
        container = Container()

        def db_factory() -> Database:
            return Database()

        def repo_factory(db: Database) -> Repository:
            return Repository(db)

        container.register(Database, db_factory)
        container.register(Repository, repo_factory)

        container.compile()

        for registration in container._providers.values():
            assert registration.injection_plan is not None


class TestContainerResolution:
    """Test dependency resolution."""

    def test_resolve_singleton(self):
        """Should resolve singleton dependency."""
        container = Container()

        def db_factory() -> Database:
            return Database("test-db")

        container.register(Database, db_factory, scope=SINGLETON)
        container.compile()

        db1 = container.get(Database)
        db2 = container.get(Database)

        assert db1 is db2
        assert db1.url == "test-db"

    def test_resolve_with_dependencies(self):
        """Should resolve dependency with its dependencies injected."""
        container = Container()

        def db_factory() -> Database:
            return Database("test-db")

        def repo_factory(db: Database) -> Repository:
            return Repository(db)

        container.register(Database, db_factory)
        container.register(Repository, repo_factory)
        container.compile()

        repo = container.get(Repository)

        assert isinstance(repo, Repository)
        assert isinstance(repo.db, Database)
        assert repo.db.url == "test-db"

    def test_resolve_deep_dependency_chain(self):
        """Should resolve deep dependency chains."""
        container = Container()

        def db_factory() -> Database:
            return Database()

        def repo_factory(db: Database) -> Repository:
            return Repository(db)

        def service_factory(repo: Repository) -> Service:
            return Service(repo)

        container.register(Database, db_factory)
        container.register(Repository, repo_factory)
        container.register(Service, service_factory)
        container.compile()

        service = container.get(Service)

        assert isinstance(service, Service)
        assert isinstance(service.repo, Repository)
        assert isinstance(service.repo.db, Database)

    def test_resolve_with_qualifier(self):
        """Should resolve provider by qualifier."""
        container = Container()

        def primary_db() -> Database:
            return Database("primary")

        def secondary_db() -> Database:
            return Database("secondary")

        container.register(Database, primary_db, qualifier="primary")
        container.register(Database, secondary_db, qualifier="secondary")
        container.compile()

        primary = container.get(Database, qualifier="primary")
        secondary = container.get(Database, qualifier="secondary")

        assert primary.url == "primary"
        assert secondary.url == "secondary"

    def test_resolve_request_scoped_dependency(self):
        """Should resolve request-scoped dependency within request context."""
        container = Container()

        def request_service() -> RequestScopedService:
            return RequestScopedService()

        container.register(RequestScopedService, request_service, scope=Scope.REQUEST)
        container.compile()

        with ScopeContext.request():
            svc1 = container.get(RequestScopedService)
            svc2 = container.get(RequestScopedService)
            # Should be same instance within request
            assert svc1 is svc2

        # Different request should get different instance
        with ScopeContext.request():
            svc3 = container.get(RequestScopedService)
            assert svc1 is not svc3

    def test_resolve_task_scoped_dependency(self):
        """Should resolve task-scoped dependency within task context."""
        container = Container()

        def task_service() -> TaskScopedService:
            return TaskScopedService()

        container.register(TaskScopedService, task_service, scope=Scope.TASK)
        container.compile()

        with ScopeContext.task():
            svc1 = container.get(TaskScopedService)
            svc2 = container.get(TaskScopedService)
            # Should be same instance within task
            assert svc1 is svc2

        # Different task should get different instance
        with ScopeContext.task():
            svc3 = container.get(TaskScopedService)
            assert svc1 is not svc3

    def test_resolve_request_scoped_outside_context_raises_error(self):
        """Should raise error when resolving request-scoped dependency outside context."""
        container = Container()

        def request_service() -> RequestScopedService:
            return RequestScopedService()

        container.register(RequestScopedService, request_service, scope=Scope.REQUEST)
        container.compile()

        with pytest.raises(DIError, match="outside of REQUEST context"):
            container.get(RequestScopedService)

    def test_resolve_missing_provider_raises_error(self):
        """Should raise error when resolving missing provider."""
        container = Container()
        container.compile()

        with pytest.raises(ProviderNotFoundError):
            container.get(Database)

    def test_resolve_before_compile_raises_error(self):
        """Should raise error when resolving before compilation."""
        container = Container()

        def db_factory() -> Database:
            return Database()

        container.register(Database, db_factory)

        with pytest.raises(DIError, match="must be compiled"):
            container.get(Database)


class TestContainerOverrides:
    """Test container overrides for testing."""

    def test_override_provider(self):
        """Should override provider for testing."""
        container = Container()

        def db_factory() -> Database:
            return Database("real")

        container.register(Database, db_factory)
        container.compile()

        # Normal resolution
        real_db = container.get(Database)
        assert real_db.url == "real"

        # Override for testing
        with container.override({Database: lambda: Database("fake")}):
            fake_db = container.get(Database)
            assert fake_db.url == "fake"

        # Back to normal after override
        real_db2 = container.get(Database)
        assert real_db2.url == "real"

    def test_nested_overrides(self):
        """Should support nested overrides."""
        container = Container()

        def db_factory() -> Database:
            return Database("real")

        container.register(Database, db_factory)
        container.compile()

        with container.override({Database: lambda: Database("fake1")}):
            db1 = container.get(Database)
            assert db1.url == "fake1"

            with container.override({Database: lambda: Database("fake2")}):
                db2 = container.get(Database)
                assert db2.url == "fake2"

            db3 = container.get(Database)
            assert db3.url == "fake1"


class TestContainerThreadSafety:
    """Test container thread safety."""

    def test_singleton_thread_safety(self):
        """Should resolve singleton safely across threads."""
        container = Container()
        instances = []

        def db_factory() -> Database:
            # Simulate some work
            import time

            time.sleep(0.001)
            return Database()

        container.register(Database, db_factory)
        container.compile()

        def resolve():
            instances.append(container.get(Database))

        threads = [threading.Thread(target=resolve) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get the same instance
        assert len({id(instance) for instance in instances}) == 1


class TestContainerEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_type_annotation_raises_error(self):
        """Should raise error for missing type annotations."""
        container = Container()

        def bad_factory(db) -> Repository:  # Missing type annotation
            return Repository(db)  # type: ignore

        container.register(Repository, bad_factory)

        with pytest.raises(DIError, match="missing type annotation"):
            container.compile()

    def test_resolve_with_annotated_qualifier(self):
        """Should resolve dependency with Annotated qualifier."""
        container = Container()

        def primary_db() -> Database:
            return Database("primary")

        def secondary_db() -> Database:
            return Database("secondary")

        def repo_factory(db: Annotated[Database, Qualifier("primary")]) -> Repository:
            return Repository(db)

        container.register(Database, primary_db, qualifier="primary")
        container.register(Database, secondary_db, qualifier="secondary")
        container.register(Repository, repo_factory)
        container.compile()

        repo = container.get(Repository)
        assert repo.db.url == "primary"
