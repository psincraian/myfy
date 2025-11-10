"""
Performance tests for DI container and core components.

Tests scalability, throughput, and resource usage.
"""

import threading
import time

import pytest

from myfy.core.di.container import Container
from myfy.core.di.scopes import SINGLETON, Scope

from .conftest import ScopeContext  # Test helper


@pytest.mark.slow
class TestContainerPerformance:
    """Test DI container performance and scalability."""

    def test_container_scales_with_many_providers(self):
        """Should handle large numbers of providers efficiently."""
        container = Container()

        # Register 1000 providers
        def make_factory(val):
            def factory():
                return f"value{val}"

            return factory

        for i in range(1000):
            container.register(f"Service{i}", make_factory(i), scope=SINGLETON)

        # Compilation should be reasonably fast
        start = time.time()
        container.compile()
        compile_time = time.time() - start

        assert compile_time < 2.0, f"Compilation took {compile_time}s, expected < 2s"

        # Resolution should be fast
        start = time.time()
        container.get("Service500")
        resolve_time = time.time() - start

        assert resolve_time < 0.01, f"Resolution took {resolve_time}s, expected < 0.01s"

    def test_deep_dependency_chain_performance(self):
        """Should handle deep dependency chains efficiently."""
        container = Container()

        # Create a chain of 50 dependencies
        class Service0:
            pass

        container.register("Service0", lambda: Service0(), scope=SINGLETON)

        for i in range(1, 50):
            prev_name = f"Service{i - 1}"
            curr_val = f"Service{i}"

            # Create factory with proper closure
            def make_factory(prev, curr):
                def factory():
                    container.get(prev)
                    return curr

                return factory

            container.register(f"Service{i}", make_factory(prev_name, curr_val), scope=SINGLETON)

        start = time.time()
        container.compile()
        compile_time = time.time() - start

        assert compile_time < 1.0, f"Compilation took {compile_time}s"

        start = time.time()
        container.get("Service49")
        resolve_time = time.time() - start

        assert resolve_time < 0.1, f"Resolution took {resolve_time}s"

    def test_concurrent_resolution_performance(self):
        """Should handle concurrent resolutions efficiently."""
        container = Container()

        class SharedService:
            def __init__(self):
                # Simulate some work
                time.sleep(0.001)
                self.value = "test"

        container.register(SharedService, lambda: SharedService(), scope=SINGLETON)
        container.compile()

        results = []
        errors = []

        def resolve():
            try:
                start = time.time()
                service = container.get(SharedService)
                duration = time.time() - start
                results.append((service, duration))
            except Exception as e:
                errors.append(e)

        # 100 concurrent resolutions
        threads = [threading.Thread(target=resolve) for _ in range(100)]

        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.time() - start

        # All should succeed
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 100

        # All should get the same instance
        instances = {id(r[0]) for r in results}
        assert len(instances) == 1, "Should all get same singleton instance"

        # Should complete in reasonable time (not serialize all 100 requests)
        assert total_time < 1.0, f"Took {total_time}s for 100 concurrent requests"

    def test_request_scope_memory_cleanup(self):
        """Should clean up request-scoped dependencies properly."""
        container = Container()

        class RequestService:
            instances_created = 0

            def __init__(self):
                RequestService.instances_created += 1
                self.data = "x" * 1000  # 1KB of data

        container.register(RequestService, lambda: RequestService(), scope=Scope.REQUEST)
        container.compile()

        initial_count = RequestService.instances_created

        # Simulate 100 requests
        for _ in range(100):
            with ScopeContext.request():
                container.get(RequestService)

        # Should have created 100 instances
        assert RequestService.instances_created == initial_count + 100

        # Memory should be cleaned up (we can't test directly, but at least no crash)
        # In production, you'd use memory profiling tools

    @pytest.mark.slow
    def test_compilation_is_idempotent(self):
        """Should handle multiple compilations efficiently."""
        container = Container()

        for i in range(100):
            container.register(f"Service{i}", lambda: f"value{i}", scope=SINGLETON)

        # First compilation
        start = time.time()
        container.compile()
        first_time = time.time() - start

        # Subsequent compilations should be fast (no-op)
        start = time.time()
        container.compile()
        second_time = time.time() - start

        assert second_time < first_time * 0.1, "Subsequent compilations should be near-instant"


@pytest.mark.slow
class TestProviderRegistrationPerformance:
    """Test provider registration performance."""

    def test_bulk_registration_performance(self):
        """Should handle bulk provider registration efficiently."""
        container = Container()

        start = time.time()
        for i in range(10000):

            def factory(val=i):
                return f"value{val}"

            container.register(f"Service{i}", factory, scope=SINGLETON)

        registration_time = time.time() - start

        assert registration_time < 1.0, f"Registration took {registration_time}s"


class TestScopeContextPerformance:
    """Test scope context performance."""

    def test_scope_context_overhead(self):
        """Should have minimal overhead for scope context management."""
        iterations = 10000

        start = time.time()
        for _ in range(iterations):
            with ScopeContext.request():
                pass  # Just enter and exit
        total_time = time.time() - start

        avg_time = total_time / iterations
        assert avg_time < 0.0001, f"Average scope overhead: {avg_time}s per iteration"

    def test_nested_scope_contexts(self):
        """Should handle nested scope contexts efficiently."""
        container = Container()

        class OuterService:
            pass

        class InnerService:
            pass

        container.register(OuterService, lambda: OuterService(), scope=Scope.REQUEST)
        container.register(InnerService, lambda: InnerService(), scope=Scope.TASK)
        container.compile()

        iterations = 1000
        start = time.time()

        for _ in range(iterations):
            with ScopeContext.request():
                container.get(OuterService)
                with ScopeContext.task():
                    container.get(InnerService)

        total_time = time.time() - start
        avg_time = total_time / iterations

        assert avg_time < 0.001, f"Average nested scope time: {avg_time}s"


@pytest.mark.slow
class TestMemoryUsage:
    """Test memory usage patterns."""

    def test_no_memory_leak_in_repeated_resolutions(self):
        """Should not leak memory on repeated resolutions."""
        import gc

        container = Container()

        class TemporaryService:
            def __init__(self):
                self.data = [0] * 1000  # Some data

        container.register(TemporaryService, lambda: TemporaryService(), scope=Scope.REQUEST)
        container.compile()

        # Force garbage collection
        gc.collect()

        # Get baseline
        initial_objects = len(gc.get_objects())

        # Simulate many requests
        for _ in range(100):
            with ScopeContext.request():
                container.get(TemporaryService)

        # Force cleanup
        gc.collect()

        # Check for memory leaks
        final_objects = len(gc.get_objects())

        # Should not have significantly more objects
        # Allow some growth for internal caches, but not 100x
        growth = final_objects - initial_objects
        assert growth < 1000, f"Object count grew by {growth}, possible memory leak"
