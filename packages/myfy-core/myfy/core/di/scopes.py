"""
Scope management for dependency injection.

Scopes control the lifetime of injected dependencies:
- SINGLETON: One instance per application
- REQUEST: One instance per request (via contextvar)
- TASK: One instance per background task (via contextvar)
"""

from contextvars import ContextVar
from enum import Enum
from typing import Any


class Scope(str, Enum):
    """Dependency scope definitions."""

    SINGLETON = "singleton"
    REQUEST = "request"
    TASK = "task"


# Scope constants for convenience
SINGLETON = Scope.SINGLETON
REQUEST = Scope.REQUEST
TASK = Scope.TASK


# Context storage for request and task scopes
_request_scope_bag: ContextVar[dict[str, Any] | None] = ContextVar[dict[str, Any] | None](
    "_request_scope_bag", default=None
)
_task_scope_bag: ContextVar[dict[str, Any] | None] = ContextVar[dict[str, Any] | None](
    "_task_scope_bag", default=None
)


class ScopeContext:
    """
    Manages scoped dependency instances via contextvars.

    Request and task scopes store instances in contextvar dictionaries,
    ensuring thread-safe and async-safe isolation.
    """

    @staticmethod
    def get_request_bag() -> dict[str, Any]:
        """
        Get the request scope bag for the current context.

        Raises RuntimeError if bag not initialized.
        The ASGI adapter should call init_request_scope() before handler execution.
        """
        bag = _request_scope_bag.get()
        if bag is None:
            raise RuntimeError(
                "Request scope not initialized. "
                "Ensure the ASGI adapter sets up the request bag before handler execution."
            )
        return bag

    @staticmethod
    def get_task_bag() -> dict[str, Any]:
        """
        Get the task scope bag for the current context.

        Raises RuntimeError if bag not initialized.
        """
        bag = _task_scope_bag.get()
        if bag is None:
            raise RuntimeError(
                "Task scope not initialized. "
                "Ensure the task runner sets up the task bag before execution."
            )
        return bag

    @staticmethod
    def init_request_scope() -> dict[str, Any]:
        """Initialize a new request scope (called by ASGI adapter)."""
        bag = {}
        _request_scope_bag.set(bag)
        return bag

    @staticmethod
    def init_task_scope() -> dict[str, Any]:
        """Initialize a new task scope (called by task runner)."""
        bag = {}
        _task_scope_bag.set(bag)
        return bag

    @staticmethod
    def clear_request_bag() -> None:
        """Clear the request scope bag (call after request finishes)."""
        _request_scope_bag.set(None)

    @staticmethod
    def clear_task_bag() -> None:
        """Clear the task scope bag (call after task finishes)."""
        _task_scope_bag.set(None)

    @staticmethod
    def get_bag_for_scope(scope: Scope) -> dict[str, Any] | None:
        """Get the appropriate bag for the given scope."""
        if scope == Scope.REQUEST:
            return ScopeContext.get_request_bag()
        if scope == Scope.TASK:
            return ScopeContext.get_task_bag()
        return None  # Singleton doesn't use a bag

    @staticmethod
    def clear_scope(scope: Scope) -> None:
        """Clear the given scope's bag."""
        if scope == Scope.REQUEST:
            ScopeContext.clear_request_bag()
        elif scope == Scope.TASK:
            ScopeContext.clear_task_bag()
