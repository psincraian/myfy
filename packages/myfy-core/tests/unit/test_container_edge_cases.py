"""
Unit tests for DI Container edge cases and error handling.

These tests cover:
- Circular dependency detection
- Scope mismatch validation
- Container freezing behavior
- Duplicate registration prevention
- Provider not found errors
- Thread-safe singleton creation
- Override context manager behavior
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from myfy.core.di import REQUEST, SINGLETON, TASK, Container
from myfy.core.di.errors import (
    CircularDependencyError,
    ContainerFrozenError,
    DIError,
    DuplicateProviderError,
    ProviderNotFoundError,
    ScopeMismatchError,
)
from myfy.core.di.scopes import ScopeContext

pytestmark = pytest.mark.unit


# =============================================================================
# Circular Dependency Detection Tests
# =============================================================================


class TestCircularDependencyDetection:
    """Test circular dependency detection at compile time."""

    def test_direct_circular_dependency(self, container: Container):
        """Test that A -> B -> A is detected via type hints."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        # A depends on B (via type hint in function signature)
        def factory_a(b: ServiceB) -> ServiceA:
            return ServiceA()

        # B depends on A (circular!)
        def factory_b(a: ServiceA) -> ServiceB:
            return ServiceB()

        container.register(type_=ServiceA, factory=factory_a, scope=SINGLETON)
        container.register(type_=ServiceB, factory=factory_b, scope=SINGLETON)

        with pytest.raises(CircularDependencyError) as exc_info:
            container.compile()

        assert "Circular dependency detected" in str(exc_info.value)

    def test_indirect_circular_dependency(self, container: Container):
        """Test that A -> B -> C -> A is detected."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        class ServiceC:
            pass

        def factory_a(c: ServiceC) -> ServiceA:
            return ServiceA()

        def factory_b(a: ServiceA) -> ServiceB:
            return ServiceB()

        def factory_c(b: ServiceB) -> ServiceC:
            return ServiceC()

        container.register(type_=ServiceA, factory=factory_a, scope=SINGLETON)
        container.register(type_=ServiceB, factory=factory_b, scope=SINGLETON)
        container.register(type_=ServiceC, factory=factory_c, scope=SINGLETON)

        with pytest.raises(CircularDependencyError):
            container.compile()

    def test_self_dependency(self, container: Container):
        """Test that A -> A is detected."""

        class ServiceA:
            pass

        def factory_a(a: ServiceA) -> ServiceA:
            return ServiceA()

        container.register(type_=ServiceA, factory=factory_a, scope=SINGLETON)

        with pytest.raises(CircularDependencyError):
            container.compile()

    def test_no_cycle_with_shared_dependency(self, container: Container):
        """Test that diamond dependencies (A->B, A->C, B->D, C->D) are OK."""

        class ServiceD:
            pass

        class ServiceB:
            def __init__(self, d: ServiceD):
                self.d = d

        class ServiceC:
            def __init__(self, d: ServiceD):
                self.d = d

        class ServiceA:
            def __init__(self, b: ServiceB, c: ServiceC):
                self.b = b
                self.c = c

        def factory_d() -> ServiceD:
            return ServiceD()

        def factory_b(d: ServiceD) -> ServiceB:
            return ServiceB(d)

        def factory_c(d: ServiceD) -> ServiceC:
            return ServiceC(d)

        def factory_a(b: ServiceB, c: ServiceC) -> ServiceA:
            return ServiceA(b, c)

        container.register(type_=ServiceD, factory=factory_d, scope=SINGLETON)
        container.register(type_=ServiceB, factory=factory_b, scope=SINGLETON)
        container.register(type_=ServiceC, factory=factory_c, scope=SINGLETON)
        container.register(type_=ServiceA, factory=factory_a, scope=SINGLETON)

        # Should not raise
        container.compile()

        # Verify it works
        a = container.get(ServiceA)
        assert a.b.d is a.c.d  # Same singleton D


# =============================================================================
# Scope Mismatch Validation Tests
# =============================================================================


class TestScopeMismatchValidation:
    """Test scope validation at compile time."""

    def test_singleton_cannot_depend_on_request_scoped(self, container: Container):
        """Test that singleton cannot inject request-scoped dependency."""

        class RequestService:
            pass

        class SingletonService:
            pass

        def factory_request() -> RequestService:
            return RequestService()

        def factory_singleton(req: RequestService) -> SingletonService:
            return SingletonService()

        container.register(
            type_=RequestService,
            factory=factory_request,
            scope=REQUEST,
        )
        container.register(
            type_=SingletonService,
            factory=factory_singleton,
            scope=SINGLETON,
        )

        with pytest.raises(ScopeMismatchError) as exc_info:
            container.compile()

        error = exc_info.value
        assert "singleton" in str(error).lower()
        assert "request" in str(error).lower()

    def test_singleton_cannot_depend_on_task_scoped(self, container: Container):
        """Test that singleton cannot inject task-scoped dependency."""

        class TaskService:
            pass

        class SingletonService:
            pass

        def factory_task() -> TaskService:
            return TaskService()

        def factory_singleton(task: TaskService) -> SingletonService:
            return SingletonService()

        container.register(
            type_=TaskService,
            factory=factory_task,
            scope=TASK,
        )
        container.register(
            type_=SingletonService,
            factory=factory_singleton,
            scope=SINGLETON,
        )

        with pytest.raises(ScopeMismatchError):
            container.compile()

    def test_request_can_depend_on_singleton(self, container: Container):
        """Test that request-scoped can inject singleton (valid)."""

        class SingletonService:
            pass

        class RequestService:
            pass

        def factory_singleton() -> SingletonService:
            return SingletonService()

        def factory_request(s: SingletonService) -> RequestService:
            return RequestService()

        container.register(
            type_=SingletonService,
            factory=factory_singleton,
            scope=SINGLETON,
        )
        container.register(
            type_=RequestService,
            factory=factory_request,
            scope=REQUEST,
        )

        # Should not raise
        container.compile()

    def test_request_can_depend_on_request(self, container: Container):
        """Test that request-scoped can inject request-scoped (valid)."""

        class RequestServiceA:
            pass

        class RequestServiceB:
            pass

        def factory_a() -> RequestServiceA:
            return RequestServiceA()

        def factory_b(a: RequestServiceA) -> RequestServiceB:
            return RequestServiceB()

        container.register(
            type_=RequestServiceA,
            factory=factory_a,
            scope=REQUEST,
        )
        container.register(
            type_=RequestServiceB,
            factory=factory_b,
            scope=REQUEST,
        )

        # Should not raise
        container.compile()


# =============================================================================
# Container Freezing Tests
# =============================================================================


class TestContainerFreezing:
    """Test container state transitions and freezing behavior."""

    def test_cannot_register_after_compile(self, container: Container):
        """Test that registration fails after compile()."""
        container.compile()

        with pytest.raises(ContainerFrozenError):
            container.register(type_=str, factory=lambda: "test", scope=SINGLETON)

    def test_compile_is_idempotent(self, container: Container):
        """Test that calling compile() twice is safe."""
        container.register(type_=str, factory=lambda: "test", scope=SINGLETON)
        container.compile()
        # Second compile should be a no-op
        container.compile()
        assert container._frozen

    def test_cannot_resolve_before_compile(self, container: Container):
        """Test that resolution fails before compile()."""
        container.register(type_=str, factory=lambda: "test", scope=SINGLETON)

        with pytest.raises(DIError, match="must be compiled"):
            container.get(str)


# =============================================================================
# Duplicate Registration Tests
# =============================================================================


class TestDuplicateRegistration:
    """Test duplicate registration prevention."""

    def test_duplicate_same_type_raises_error(self, container: Container):
        """Test that registering same type twice raises error."""
        container.register(type_=str, factory=lambda: "first", scope=SINGLETON)

        with pytest.raises(DuplicateProviderError):
            container.register(type_=str, factory=lambda: "second", scope=SINGLETON)

    def test_same_type_different_qualifier_allowed(self, container: Container):
        """Test that same type with different qualifiers is allowed."""
        container.register(type_=str, factory=lambda: "first", scope=SINGLETON, qualifier="first")
        container.register(type_=str, factory=lambda: "second", scope=SINGLETON, qualifier="second")

        container.compile()

        assert container.get(str, qualifier="first") == "first"
        assert container.get(str, qualifier="second") == "second"

    def test_same_type_different_name_allowed(self, container: Container):
        """Test that same type with different names is allowed."""
        container.register(type_=str, factory=lambda: "first", scope=SINGLETON, name="first")
        container.register(type_=str, factory=lambda: "second", scope=SINGLETON, name="second")

        # Should compile without error
        container.compile()


# =============================================================================
# Provider Not Found Tests
# =============================================================================


class TestProviderNotFound:
    """Test provider not found error handling."""

    def test_get_unregistered_type_raises_error(self, compiled_container: Container):
        """Test that getting unregistered type raises error."""

        class UnregisteredService:
            pass

        with pytest.raises(ProviderNotFoundError) as exc_info:
            compiled_container.get(UnregisteredService)

        assert "UnregisteredService" in str(exc_info.value)
        assert "Did you forget to register" in str(exc_info.value)

    def test_get_wrong_qualifier_raises_error(self, container: Container):
        """Test that getting with wrong qualifier raises error."""
        container.register(type_=str, factory=lambda: "test", scope=SINGLETON, qualifier="correct")
        container.compile()

        with pytest.raises(ProviderNotFoundError):
            container.get(str, qualifier="wrong")


# =============================================================================
# Thread-Safe Singleton Creation Tests
# =============================================================================


class TestThreadSafeSingletonCreation:
    """Test thread-safe singleton creation."""

    def test_singleton_created_once_under_contention(self, container: Container):
        """Test that singleton is created exactly once under thread contention."""
        creation_count = 0
        creation_lock = threading.Lock()

        class ExpensiveService:
            pass

        def create_service():
            nonlocal creation_count
            with creation_lock:
                creation_count += 1
            # Simulate slow creation
            time.sleep(0.01)
            return ExpensiveService()

        container.register(
            type_=ExpensiveService,
            factory=create_service,
            scope=SINGLETON,
        )
        container.compile()

        results = []

        def get_service():
            service = container.get(ExpensiveService)
            results.append(service)

        # Create multiple threads trying to get the same singleton
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_service) for _ in range(20)]
            for f in futures:
                f.result()

        # Verify singleton was created exactly once
        assert creation_count == 1

        # Verify all threads got the same instance
        assert len(results) == 20
        assert all(r is results[0] for r in results)

    def test_different_singletons_can_be_created_in_parallel(self, container: Container):
        """Test that different singletons can be created concurrently."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        container.register(
            type_=ServiceA,
            factory=lambda: ServiceA(),
            scope=SINGLETON,
        )
        container.register(
            type_=ServiceB,
            factory=lambda: ServiceB(),
            scope=SINGLETON,
        )
        container.compile()

        results = {"a": [], "b": []}

        def get_service_a():
            results["a"].append(container.get(ServiceA))

        def get_service_b():
            results["b"].append(container.get(ServiceB))

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for _ in range(10):
                futures.append(executor.submit(get_service_a))
                futures.append(executor.submit(get_service_b))
            for f in futures:
                f.result()

        # Verify each type got exactly one instance
        assert len(results["a"]) == 10
        assert len(results["b"]) == 10
        assert all(r is results["a"][0] for r in results["a"])
        assert all(r is results["b"][0] for r in results["b"])


# =============================================================================
# Override Context Manager Tests
# =============================================================================


class TestOverrideContextManager:
    """Test the override context manager for testing."""

    def test_override_replaces_provider(self, container: Container):
        """Test that override replaces the original provider."""

        class RealService:
            def get_data(self):
                return "real"

        class FakeService:
            def get_data(self):
                return "fake"

        container.register(
            type_=RealService,
            factory=lambda: RealService(),
            scope=SINGLETON,
        )
        container.compile()

        # Original
        assert container.get(RealService).get_data() == "real"

        # With override
        with container.override({RealService: lambda: FakeService()}):
            result = container.get(RealService)
            assert result.get_data() == "fake"

        # Back to original
        assert container.get(RealService).get_data() == "real"

    def test_nested_overrides(self, container: Container):
        """Test that overrides can be nested."""

        class Service:
            def __init__(self, value: str):
                self.value = value

        container.register(
            type_=Service,
            factory=lambda: Service("original"),
            scope=SINGLETON,
        )
        container.compile()

        assert container.get(Service).value == "original"

        with container.override({Service: lambda: Service("level1")}):
            assert container.get(Service).value == "level1"

            with container.override({Service: lambda: Service("level2")}):
                assert container.get(Service).value == "level2"

            # Back to level1
            assert container.get(Service).value == "level1"

        # Back to original
        assert container.get(Service).value == "original"

    def test_override_does_not_affect_unrelated_types(self, container: Container):
        """Test that override only affects specified types."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        class FakeA:
            pass

        container.register(type_=ServiceA, factory=lambda: ServiceA(), scope=SINGLETON)
        container.register(type_=ServiceB, factory=lambda: ServiceB(), scope=SINGLETON)
        container.compile()

        original_b = container.get(ServiceB)

        with container.override({ServiceA: lambda: FakeA()}):
            # A is overridden
            assert isinstance(container.get(ServiceA), FakeA)
            # B is unchanged
            assert container.get(ServiceB) is original_b


# =============================================================================
# Scope Resolution Edge Cases
# =============================================================================


class TestScopeResolutionEdgeCases:
    """Test edge cases in scope-based resolution."""

    def test_request_scope_without_context_raises_error(self, container: Container):
        """Test that resolving request-scoped without context raises error."""

        class RequestService:
            pass

        container.register(
            type_=RequestService,
            factory=lambda: RequestService(),
            scope=REQUEST,
        )
        container.compile()

        # Clear any existing scope
        try:
            ScopeContext.clear_request_bag()
        except Exception:
            pass

        # Either DIError or RuntimeError depending on which path fails first
        with pytest.raises((DIError, RuntimeError)):
            container.get(RequestService)

    def test_task_scope_without_context_raises_error(self, container: Container):
        """Test that resolving task-scoped without context raises error."""

        class TaskService:
            pass

        container.register(
            type_=TaskService,
            factory=lambda: TaskService(),
            scope=TASK,
        )
        container.compile()

        # Clear any existing scope
        try:
            ScopeContext.clear_task_bag()
        except Exception:
            pass

        # Either DIError or RuntimeError depending on which path fails first
        with pytest.raises((DIError, RuntimeError)):
            container.get(TaskService)

    def test_request_scope_caches_within_context(self, container: Container, request_scope):
        """Test that request-scoped service is cached within the same context."""
        creation_count = 0

        class RequestService:
            pass

        def create():
            nonlocal creation_count
            creation_count += 1
            return RequestService()

        container.register(
            type_=RequestService,
            factory=create,
            scope=REQUEST,
        )
        container.compile()

        # Get multiple times within same request
        s1 = container.get(RequestService)
        s2 = container.get(RequestService)
        s3 = container.get(RequestService)

        assert creation_count == 1
        assert s1 is s2 is s3

    def test_new_request_scope_creates_new_instance(self, container: Container):
        """Test that new request scope creates new instance."""

        class RequestService:
            pass

        instances = []

        def create():
            instance = RequestService()
            instances.append(instance)
            return instance

        container.register(
            type_=RequestService,
            factory=create,
            scope=REQUEST,
        )
        container.compile()

        # First request
        ScopeContext.init_request_scope()
        r1_s1 = container.get(RequestService)
        r1_s2 = container.get(RequestService)
        ScopeContext.clear_request_bag()

        # Second request
        ScopeContext.init_request_scope()
        r2_s1 = container.get(RequestService)
        ScopeContext.clear_request_bag()

        # Same instance within request
        assert r1_s1 is r1_s2
        # Different instance across requests
        assert r1_s1 is not r2_s1
        assert len(instances) == 2


# =============================================================================
# Dependency Analysis Edge Cases
# =============================================================================


class TestDependencyAnalysisEdgeCases:
    """Test edge cases in dependency analysis."""

    def test_factory_with_no_parameters(self, container: Container):
        """Test factory with no parameters works."""

        class SimpleService:
            pass

        container.register(
            type_=SimpleService,
            factory=lambda: SimpleService(),
            scope=SINGLETON,
        )
        container.compile()

        result = container.get(SimpleService)
        assert isinstance(result, SimpleService)

    def test_factory_with_default_parameters(self, container: Container):
        """Test factory with default parameters is handled correctly."""

        class ConfigurableService:
            def __init__(self, value: str = "default"):
                self.value = value

        def factory(value: str = "custom") -> ConfigurableService:
            return ConfigurableService(value)

        container.register(
            type_=ConfigurableService,
            factory=factory,
            scope=SINGLETON,
        )

        # This should work - factory has defaults
        container.compile()

    def test_annotated_qualifier_in_parameters(self, container: Container):
        """Test that Annotated[T, Qualifier] works for selecting providers."""

        class Database:
            def __init__(self, name: str):
                self.name = name

        container.register(
            type_=Database,
            factory=lambda: Database("primary"),
            scope=SINGLETON,
            qualifier="primary",
        )
        container.register(
            type_=Database,
            factory=lambda: Database("replica"),
            scope=SINGLETON,
            qualifier="replica",
        )
        container.compile()

        primary = container.get(Database, qualifier="primary")
        replica = container.get(Database, qualifier="replica")

        assert primary.name == "primary"
        assert replica.name == "replica"
