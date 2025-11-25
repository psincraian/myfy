"""
Unit tests for ScopeContext edge cases.

These tests cover:
- Context variable isolation
- Nested scope contexts
- Error handling for uninitialized scopes
- Scope cleanup behavior
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

from myfy.core.di.scopes import (
    REQUEST,
    SINGLETON,
    TASK,
    Scope,
    ScopeContext,
)

pytestmark = pytest.mark.unit


# =============================================================================
# Request Scope Tests
# =============================================================================


class TestRequestScopeContext:
    """Test request scope context behavior."""

    def test_init_request_scope_returns_empty_dict(self):
        """Test that init_request_scope returns an empty dict."""
        bag = ScopeContext.init_request_scope()
        try:
            assert isinstance(bag, dict)
            assert len(bag) == 0
        finally:
            ScopeContext.clear_request_bag()

    def test_get_request_bag_after_init(self):
        """Test that get_request_bag returns the initialized bag."""
        bag = ScopeContext.init_request_scope()
        try:
            bag["test_key"] = "test_value"
            retrieved = ScopeContext.get_request_bag()
            assert retrieved is bag
            assert retrieved["test_key"] == "test_value"
        finally:
            ScopeContext.clear_request_bag()

    def test_get_request_bag_without_init_raises_error(self):
        """Test that get_request_bag raises error when not initialized."""
        # Ensure clean state
        try:
            ScopeContext.clear_request_bag()
        except Exception:
            pass

        with pytest.raises(RuntimeError, match="Request scope not initialized"):
            ScopeContext.get_request_bag()

    def test_clear_request_bag_removes_context(self):
        """Test that clear_request_bag removes the context."""
        ScopeContext.init_request_scope()
        ScopeContext.clear_request_bag()

        with pytest.raises(RuntimeError):
            ScopeContext.get_request_bag()

    def test_request_scope_isolation_between_async_tasks(self):
        """Test that request scopes are isolated between concurrent async tasks."""

        async def task_with_scope(task_id: int, results: dict):
            bag = ScopeContext.init_request_scope()
            bag["task_id"] = task_id

            # Simulate some async work
            await asyncio.sleep(0.01)

            # Verify isolation
            retrieved = ScopeContext.get_request_bag()
            results[task_id] = retrieved.get("task_id")

            ScopeContext.clear_request_bag()

        async def run_test():
            results = {}
            await asyncio.gather(
                task_with_scope(1, results),
                task_with_scope(2, results),
                task_with_scope(3, results),
            )
            return results

        results = asyncio.run(run_test())

        # Each task should see only its own task_id
        assert results[1] == 1
        assert results[2] == 2
        assert results[3] == 3


# =============================================================================
# Task Scope Tests
# =============================================================================


class TestTaskScopeContext:
    """Test task scope context behavior."""

    def test_init_task_scope_returns_empty_dict(self):
        """Test that init_task_scope returns an empty dict."""
        bag = ScopeContext.init_task_scope()
        try:
            assert isinstance(bag, dict)
            assert len(bag) == 0
        finally:
            ScopeContext.clear_task_bag()

    def test_get_task_bag_after_init(self):
        """Test that get_task_bag returns the initialized bag."""
        bag = ScopeContext.init_task_scope()
        try:
            bag["job_id"] = "job123"
            retrieved = ScopeContext.get_task_bag()
            assert retrieved is bag
            assert retrieved["job_id"] == "job123"
        finally:
            ScopeContext.clear_task_bag()

    def test_get_task_bag_without_init_raises_error(self):
        """Test that get_task_bag raises error when not initialized."""
        try:
            ScopeContext.clear_task_bag()
        except Exception:
            pass

        with pytest.raises(RuntimeError, match="Task scope not initialized"):
            ScopeContext.get_task_bag()

    def test_clear_task_bag_removes_context(self):
        """Test that clear_task_bag removes the context."""
        ScopeContext.init_task_scope()
        ScopeContext.clear_task_bag()

        with pytest.raises(RuntimeError):
            ScopeContext.get_task_bag()


# =============================================================================
# Scope Bag Selection Tests
# =============================================================================


class TestGetBagForScope:
    """Test get_bag_for_scope behavior."""

    def test_get_bag_for_request_scope(self, request_scope):
        """Test get_bag_for_scope with REQUEST scope."""
        bag = ScopeContext.get_bag_for_scope(Scope.REQUEST)
        assert bag is request_scope

    def test_get_bag_for_task_scope(self, task_scope):
        """Test get_bag_for_scope with TASK scope."""
        bag = ScopeContext.get_bag_for_scope(Scope.TASK)
        assert bag is task_scope

    def test_get_bag_for_singleton_scope_returns_none(self):
        """Test get_bag_for_scope with SINGLETON returns None."""
        bag = ScopeContext.get_bag_for_scope(Scope.SINGLETON)
        assert bag is None


# =============================================================================
# Clear Scope Tests
# =============================================================================


class TestClearScope:
    """Test clear_scope behavior."""

    def test_clear_scope_request(self):
        """Test clear_scope clears REQUEST scope."""
        ScopeContext.init_request_scope()
        ScopeContext.clear_scope(Scope.REQUEST)

        with pytest.raises(RuntimeError):
            ScopeContext.get_request_bag()

    def test_clear_scope_task(self):
        """Test clear_scope clears TASK scope."""
        ScopeContext.init_task_scope()
        ScopeContext.clear_scope(Scope.TASK)

        with pytest.raises(RuntimeError):
            ScopeContext.get_task_bag()

    def test_clear_scope_singleton_is_no_op(self):
        """Test clear_scope with SINGLETON is a no-op."""
        # Should not raise
        ScopeContext.clear_scope(Scope.SINGLETON)


# =============================================================================
# Concurrent Access Tests
# =============================================================================


class TestConcurrentScopeAccess:
    """Test concurrent access to scope contexts."""

    def test_thread_isolation_for_request_scope(self):
        """Test that request scopes are isolated between threads."""
        results = {}
        errors = []

        def thread_task(thread_id: int):
            try:
                bag = ScopeContext.init_request_scope()
                bag["thread_id"] = thread_id

                # Small delay to increase chance of interleaving
                import time

                time.sleep(0.01)

                # Verify our thread_id is still correct
                retrieved = ScopeContext.get_request_bag()
                results[thread_id] = retrieved.get("thread_id")

                ScopeContext.clear_request_bag()
            except Exception as e:
                errors.append((thread_id, str(e)))

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(thread_task, i) for i in range(10)]
            for f in futures:
                f.result()

        assert not errors, f"Errors occurred: {errors}"
        # Each thread should see only its own thread_id
        for thread_id, value in results.items():
            assert value == thread_id, f"Thread {thread_id} saw {value}"

    def test_independent_request_and_task_scopes(self, request_scope, task_scope):
        """Test that request and task scopes are independent."""
        request_scope["scope"] = "request"
        task_scope["scope"] = "task"

        # Verify independence
        assert ScopeContext.get_request_bag()["scope"] == "request"
        assert ScopeContext.get_task_bag()["scope"] == "task"


# =============================================================================
# Scope Enum Tests
# =============================================================================


class TestScopeEnum:
    """Test Scope enum behavior."""

    def test_scope_values(self):
        """Test that scope enum has expected values."""
        assert Scope.SINGLETON.value == "singleton"
        assert Scope.REQUEST.value == "request"
        assert Scope.TASK.value == "task"

    def test_scope_string_representation(self):
        """Test scope string representation."""
        assert str(Scope.SINGLETON) == "Scope.SINGLETON"
        assert str(REQUEST) == "Scope.REQUEST"

    def test_scope_equality(self):
        """Test scope equality comparisons."""
        assert SINGLETON == Scope.SINGLETON
        assert REQUEST == Scope.REQUEST
        assert TASK == Scope.TASK

    def test_scope_membership(self):
        """Test scope membership check."""
        all_scopes = list(Scope)
        assert Scope.SINGLETON in all_scopes
        assert Scope.REQUEST in all_scopes
        assert Scope.TASK in all_scopes
        assert len(all_scopes) == 3


# =============================================================================
# Edge Cases and Error Conditions
# =============================================================================


class TestScopeEdgeCases:
    """Test edge cases in scope handling."""

    def test_double_init_request_scope_creates_new_bag(self):
        """Test that double init replaces the previous bag."""
        first_bag = ScopeContext.init_request_scope()
        first_bag["key"] = "first"

        second_bag = ScopeContext.init_request_scope()

        try:
            # Second init should have created a new empty bag
            assert "key" not in second_bag
            # The bags should be different objects
            assert first_bag is not second_bag
        finally:
            ScopeContext.clear_request_bag()

    def test_clear_non_existent_request_scope(self):
        """Test that clearing non-existent request scope is safe."""
        # Ensure clean state
        try:
            ScopeContext.clear_request_bag()
        except Exception:
            pass

        # Should not raise (sets to None which is fine)
        ScopeContext.clear_request_bag()

    def test_scope_survives_exception(self, request_scope):
        """Test that scope context survives exceptions in user code."""
        request_scope["key"] = "value"

        try:
            raise ValueError("test error")
        except ValueError:
            pass

        # Scope should still be valid
        assert ScopeContext.get_request_bag()["key"] == "value"
