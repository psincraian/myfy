"""
Task wrapper class with type-safe dispatch.

Provides the Task[P, R] class that wraps decorated functions.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    ParamSpec,
    TypeVar,
    get_type_hints,
)

from .context import TaskContext
from .errors import TaskSerializationError, TasksModuleNotConfiguredError
from .models import TaskStatus
from .result import TaskResult

if TYPE_CHECKING:
    from myfy.data import SessionFactory

    from .queue import TaskQueue

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

# Module-level references set by TasksModule
_task_queue: TaskQueue | None = None
_session_factory: SessionFactory | None = None


def _set_module_refs(queue: TaskQueue, session_factory: SessionFactory) -> None:
    """Set module-level references (called by TasksModule)."""
    global _task_queue, _session_factory
    _task_queue = queue
    _session_factory = session_factory


def _get_queue() -> TaskQueue:
    """Get the task queue."""
    if _task_queue is None:
        raise TasksModuleNotConfiguredError("TaskQueue")
    return _task_queue


def _get_session_factory() -> SessionFactory:
    """Get the session factory."""
    if _session_factory is None:
        raise TasksModuleNotConfiguredError("SessionFactory")
    return _session_factory


# Primitive types that are serialized as task arguments
_PRIMITIVE_TYPES = (str, int, float, bool, bytes, type(None))


def _is_serializable_type(t: type) -> bool:
    """
    Check if a type should be serialized as a task argument.

    Primitive types and common collections are serialized.
    Complex types (services, TaskContext) are injected at runtime.
    """
    # Handle None type
    if t is type(None):
        return True

    # Handle primitive types
    try:
        if t in _PRIMITIVE_TYPES or issubclass(t, _PRIMITIVE_TYPES):
            return True
    except TypeError:
        pass

    # Handle generic types (list, dict, etc.)
    origin = getattr(t, "__origin__", None)
    if origin is not None:
        # list[str], dict[str, int], etc.
        if origin in (list, dict, set, tuple):
            return True

    # Everything else is assumed to be injectable
    return False


class Task(Generic[P, R]):
    """
    Type-safe task wrapper preserving function signature.

    Wraps an async function decorated with @task, providing:
    - send() for dispatching tasks
    - get_result() for retrieving results

    The ParamSpec preserves the original function signature for IDE autocomplete.

    Example:
        ```python
        @task
        async def send_email(to: str, subject: str) -> None:
            ...

        # IDE knows send() accepts to: str, subject: str
        task_id = await send_email.send(to="user@example.com", subject="Hello")

        # IDE knows get_result() returns TaskResult[None]
        result = await send_email.get_result(task_id)
        ```
    """

    def __init__(
        self,
        func: Callable[P, Awaitable[R]],
        *,
        name: str | None = None,
        max_retries: int | None = None,
        retry_on: list[type[Exception]] | None = None,
    ) -> None:
        """
        Initialize task wrapper.

        Args:
            func: The async function to wrap
            name: Custom task name (default: module.qualname)
            max_retries: Override default max retries
            retry_on: Exception types that should trigger retry
        """
        self._func = func
        func_qualname = getattr(func, "__qualname__", None) or getattr(func, "__name__", "unknown")
        self._name = name or f"{func.__module__}.{func_qualname}"
        self._max_retries = max_retries
        self._retry_on = retry_on or []
        self._is_async = inspect.iscoroutinefunction(func)

        # Analyze function signature
        self._signature = inspect.signature(func)
        self._type_hints: dict[str, type] = {}
        try:
            self._type_hints = get_type_hints(func)
        except Exception:
            pass

        # Categorize parameters
        self._task_args: set[str] = set()
        self._injectable_params: dict[str, type] = {}
        self._has_context = False

        self._analyze_parameters()

    def _analyze_parameters(self) -> None:
        """Analyze function parameters to separate args from injectables."""
        for param_name in self._signature.parameters:
            param_type = self._type_hints.get(param_name)

            # TaskContext is always injected
            if param_type is TaskContext:
                self._has_context = True
                continue

            # Parameters with no type hint are assumed to be task args
            if param_type is None:
                self._task_args.add(param_name)
                continue

            # Primitive types are task arguments
            if _is_serializable_type(param_type):
                self._task_args.add(param_name)
            else:
                # Complex types are injected at runtime
                self._injectable_params[param_name] = param_type

    @property
    def name(self) -> str:
        """Fully qualified task name."""
        return self._name

    @property
    def func(self) -> Callable[P, Awaitable[R]]:
        """The wrapped function."""
        return self._func

    @property
    def is_async(self) -> bool:
        """Whether the function is async."""
        return self._is_async

    @property
    def max_retries(self) -> int | None:
        """Override max retries, or None to use default."""
        return self._max_retries

    @property
    def retry_on(self) -> list[type[Exception]]:
        """Exception types that trigger retry."""
        return self._retry_on

    @property
    def has_context(self) -> bool:
        """Whether the task accepts TaskContext."""
        return self._has_context

    @property
    def injectable_params(self) -> dict[str, type]:
        """Parameters that need DI injection."""
        return self._injectable_params.copy()

    async def send(self, *args: P.args, **kwargs: P.kwargs) -> str:
        """
        Dispatch task for async execution.

        Returns immediately with a task_id. The task will be executed
        by a worker process.

        Special kwargs with underscore prefix are dispatch options:
        - _priority: int - Higher priority tasks execute first
        - _max_retries: int - Override default max retries
        - _delay: float - Seconds to wait before executing

        Args:
            *args: Positional arguments for the task
            **kwargs: Keyword arguments for the task

        Returns:
            task_id: Unique identifier for tracking the task

        Raises:
            TasksModuleNotConfiguredError: If TasksModule not initialized
            TaskSerializationError: If arguments cannot be serialized

        Example:
            ```python
            # Simple dispatch
            task_id = await send_email.send(
                to="user@example.com",
                subject="Hello",
            )

            # With options
            task_id = await send_email.send(
                to="user@example.com",
                subject="Hello",
                _priority=10,
                _delay=60,
            )
            ```
        """
        # Extract dispatch options (underscore-prefixed kwargs)
        priority = kwargs.pop("_priority", 0)
        max_retries = kwargs.pop("_max_retries", self._max_retries)
        delay = kwargs.pop("_delay", 0)

        # Build task arguments (only serializable params)
        task_args: dict[str, Any] = {}

        # Handle positional args
        param_names = list(self._signature.parameters.keys())
        for i, value in enumerate(args):
            if i < len(param_names):
                param_name = param_names[i]
                if param_name in self._task_args:
                    task_args[param_name] = value

        # Handle keyword args
        task_args.update({k: v for k, v in kwargs.items() if k in self._task_args})

        # Validate serialization
        try:
            import json

            json.dumps(task_args)
        except (TypeError, ValueError) as e:
            raise TaskSerializationError(self._name, e) from e

        # Enqueue task
        queue = _get_queue()
        session_factory = _get_session_factory()

        async with session_factory.session_context() as session:
            task_id = await queue.enqueue(
                session,
                name=self._name,
                args=task_args,
                priority=priority,  # type: ignore[arg-type]
                max_retries=max_retries,  # type: ignore[arg-type]
                delay_seconds=delay,  # type: ignore[arg-type]
            )

        logger.info(f"Dispatched task {self._name} (id={task_id})")
        return task_id

    async def get_result(
        self,
        task_id: str,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ) -> TaskResult[R]:
        """
        Retrieve task result.

        Polls the database until the task finishes or timeout is reached.

        Args:
            task_id: The task ID returned by send()
            timeout: Maximum seconds to wait for completion
            poll_interval: Seconds between database checks

        Returns:
            TaskResult with status, value, error, and progress

        Example:
            ```python
            task_id = await send_email.send(to="user@example.com", ...)

            # Wait for result (with timeout)
            result = await send_email.get_result(task_id, timeout=60)

            if result.is_completed:
                print(f"Success: {result.value}")
            elif result.is_failed:
                print(f"Error: {result.error}")
            ```
        """
        queue = _get_queue()
        session_factory = _get_session_factory()

        start_time = asyncio.get_event_loop().time()

        while True:
            async with session_factory.session_context() as session:
                record = await queue.get_task(session, task_id)

            if record is None:
                # Task not found - return empty result
                return TaskResult(
                    task_id=task_id,
                    status=TaskStatus.PENDING,
                )

            # Build result
            progress = None
            if record.progress_current is not None and record.progress_total is not None:
                progress = (record.progress_current, record.progress_total)

            result = TaskResult[R](
                task_id=task_id,
                status=TaskStatus(record.status),
                value=record.result,
                error=record.error_message,
                traceback=record.error_traceback,
                started_at=record.started_at,
                completed_at=record.completed_at,
                progress=progress,
                progress_message=record.progress_message,
                attempt=record.retry_count + 1,
            )

            # Return if finished or timeout
            if result.is_finished:
                return result

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                return result

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    def __repr__(self) -> str:
        return f"Task(name={self._name!r})"

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Awaitable[R]:
        """
        Direct call executes the function (for testing without worker).

        Warning: This bypasses the queue and executes synchronously.
        Use send() for production task dispatch.
        """
        return self._func(*args, **kwargs)
