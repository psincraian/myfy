"""
Task decorator for defining async tasks.

Provides the @task decorator that registers functions with the TaskRegistry.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar, overload

from .registry import TaskRegistry
from .task import Task

P = ParamSpec("P")
R = TypeVar("R")


@overload
def task(func: Callable[P, Awaitable[R]]) -> Task[P, R]: ...


@overload
def task(
    *,
    name: str | None = None,
    max_retries: int | None = None,
    retry_on: list[type[Exception]] | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Task[P, R]]: ...


def task(
    func: Callable[P, Awaitable[R]] | None = None,
    *,
    name: str | None = None,
    max_retries: int | None = None,
    retry_on: list[type[Exception]] | None = None,
) -> Task[P, R] | Callable[[Callable[P, Awaitable[R]]], Task[P, R]]:
    """
    Decorator to define an async task.

    Tasks are registered in the global TaskRegistry and can be dispatched
    for async execution via send().

    Args:
        func: The async function to decorate (when used without parentheses)
        name: Custom task name (default: module.qualname)
        max_retries: Override default max retries for this task
        retry_on: Exception types that should trigger automatic retry

    Returns:
        Task wrapper with send() and get_result() methods

    Example:
        ```python
        # Simple usage
        @task
        async def send_email(to: str, subject: str, body: str) -> None:
            ...

        # With options
        @task(max_retries=5, retry_on=[ConnectionError])
        async def fetch_data(url: str) -> dict:
            ...

        # Custom name
        @task(name="emails.send")
        async def send_email(to: str) -> None:
            ...

        # Dispatch
        task_id = await send_email.send(to="user@example.com", subject="Hi")

        # Get result
        result = await send_email.get_result(task_id)
        ```
    """

    def decorator(f: Callable[P, Awaitable[R]]) -> Task[P, R]:
        task_instance = Task(
            f,
            name=name,
            max_retries=max_retries,
            retry_on=retry_on,
        )
        TaskRegistry.get_instance().register(task_instance)
        return task_instance

    if func is not None:
        # Called without parentheses: @task
        return decorator(func)

    # Called with parentheses: @task(...)
    return decorator
