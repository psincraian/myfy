"""
Test utilities for tasks module.

Provides helpers for testing tasks without a real worker.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from .config import TasksSettings
from .context import TaskContext
from .models import TasksBase
from .module import TasksModule
from .queue import TaskQueue
from .registry import TaskRegistry

if TYPE_CHECKING:
    from myfy.data import SessionFactory


@dataclass
class TaskCall:
    """Record of a task invocation during testing."""

    task_id: str
    """Unique task identifier."""

    task_name: str
    """Name of the task that was called."""

    args: dict[str, Any]
    """Arguments passed to the task."""

    result: Any = None
    """Return value if task completed."""

    error: Exception | None = None
    """Exception if task failed."""

    duration: timedelta | None = None
    """How long the task took to execute."""


@dataclass
class TestTaskRunner:
    """
    Test runner with task call tracking.

    Provides assertions and spying capabilities for testing tasks.

    Example:
        ```python
        async with test_task_runner(session_factory) as runner:
            # Execute tasks (usually via your application code)
            await process_data.send(data="test")

            # Use worker to process
            await runner.process_pending()

            # Assert
            assert runner.was_called(process_data)
            assert runner.call_count(process_data) == 1
            call = runner.last_call(process_data)
            assert call.args["data"] == "test"
        ```
    """

    module: TasksModule
    queue: TaskQueue
    session_factory: Any
    _calls: list[TaskCall] = field(default_factory=list)

    def was_called(self, task: Any) -> bool:
        """Check if a task was called."""
        task_name = getattr(task, "name", str(task))
        return any(c.task_name == task_name for c in self._calls)

    def call_count(self, task: Any) -> int:
        """Get number of times a task was called."""
        task_name = getattr(task, "name", str(task))
        return sum(1 for c in self._calls if c.task_name == task_name)

    def last_call(self, task: Any) -> TaskCall | None:
        """Get the last call record for a task."""
        task_name = getattr(task, "name", str(task))
        for call in reversed(self._calls):
            if call.task_name == task_name:
                return call
        return None

    def all_calls(self, task: Any | None = None) -> list[TaskCall]:
        """Get all call records, optionally filtered by task."""
        if task is None:
            return list(self._calls)
        task_name = getattr(task, "name", str(task))
        return [c for c in self._calls if c.task_name == task_name]

    def clear(self) -> None:
        """Clear all call records."""
        self._calls.clear()

    async def process_pending(self, max_tasks: int = 100) -> int:
        """
        Process pending tasks synchronously.

        Useful for testing task execution without a real worker.

        Args:
            max_tasks: Maximum number of tasks to process

        Returns:
            Number of tasks processed
        """
        import traceback
        from datetime import UTC, datetime

        from myfy.core.di import ScopeContext

        processed = 0
        registry = TaskRegistry.get_instance()

        while processed < max_tasks:
            # Claim tasks
            async with self.session_factory.session_context() as session:
                tasks = await self.queue.claim_tasks(session, "test-runner", batch_size=1)

            if not tasks:
                break

            for task_record in tasks:
                task_name = task_record.name
                task_id = task_record.id
                start_time = datetime.now(UTC)

                try:
                    task_def = registry.get(task_name)

                    # Initialize TASK scope
                    ScopeContext.init_task_scope()

                    try:
                        # Build kwargs
                        kwargs: dict[str, Any] = dict(task_record.args)

                        # Inject TaskContext if needed
                        if task_def.has_context:
                            ctx = TaskContext(
                                task_id=task_id,
                                attempt=task_record.retry_count + 1,
                                _queue=self.queue,
                                _session_factory=self.session_factory,
                            )
                            kwargs["ctx"] = ctx

                        # Execute
                        if task_def.is_async:
                            result = await task_def.func(**kwargs)
                        else:
                            result = task_def.func(**kwargs)

                        # Record call
                        duration = datetime.now(UTC) - start_time
                        self._calls.append(
                            TaskCall(
                                task_id=task_id,
                                task_name=task_name,
                                args=dict(task_record.args),
                                result=result,
                                duration=duration,
                            )
                        )

                        # Mark completed
                        async with self.session_factory.session_context() as session:
                            await self.queue.complete_task(session, task_id, result)

                    finally:
                        ScopeContext.clear_task_bag()

                except Exception as e:
                    # Record failure
                    duration = datetime.now(UTC) - start_time
                    self._calls.append(
                        TaskCall(
                            task_id=task_id,
                            task_name=task_name,
                            args=dict(task_record.args),
                            error=e,
                            duration=duration,
                        )
                    )

                    # Mark failed
                    async with self.session_factory.session_context() as session:
                        await self.queue.fail_task(session, task_id, str(e), traceback.format_exc())

                processed += 1

        return processed


@asynccontextmanager
async def test_task_runner(
    session_factory: SessionFactory,
    *,
    settings: TasksSettings | None = None,
    auto_create_tables: bool = True,
) -> AsyncIterator[TestTaskRunner]:
    """
    Context manager for testing tasks.

    Creates a test environment with a TasksModule and TaskQueue,
    allowing you to dispatch and process tasks synchronously.

    Args:
        session_factory: Database session factory (from test_database)
        settings: Optional custom settings
        auto_create_tables: Create tasks table (default True)

    Yields:
        TestTaskRunner with task tracking capabilities

    Example:
        ```python
        from myfy.data.testing import test_database
        from myfy.tasks.testing import test_task_runner

        async def test_my_task():
            async with test_database() as (data_module, session_factory):
                async with test_task_runner(session_factory) as runner:
                    # Dispatch task
                    task_id = await my_task.send(value="test")

                    # Process it
                    await runner.process_pending()

                    # Assert
                    assert runner.was_called(my_task)
        ```
    """
    from sqlalchemy.ext.asyncio import AsyncEngine

    from myfy.core.di import SINGLETON, Container

    settings = settings or TasksSettings()
    module = TasksModule(settings=settings, auto_create_tables=auto_create_tables)

    # Create a minimal container
    container = Container()

    # Register session factory and engine
    container.register(type(session_factory), lambda: session_factory, scope=SINGLETON)

    # Get engine from session factory
    engine = session_factory._sessionmaker.kw.get("bind")
    if engine:
        container.register(AsyncEngine, lambda: engine, scope=SINGLETON)

    # Configure module
    module.configure(container)
    container.compile()
    module.finalize(container)

    # Start module (creates tables)
    await module.start()

    try:
        yield TestTaskRunner(
            module=module,
            queue=module.get_queue(),
            session_factory=session_factory,
        )
    finally:
        await module.stop()
        # Clear registry for test isolation
        TaskRegistry.get_instance().clear()


async def create_test_tasks_table(engine: Any) -> None:
    """
    Create the tasks table for testing.

    Args:
        engine: SQLAlchemy async engine
    """
    async with engine.begin() as conn:
        await conn.run_sync(TasksBase.metadata.create_all)


async def drop_test_tasks_table(engine: Any) -> None:
    """
    Drop the tasks table for testing.

    Args:
        engine: SQLAlchemy async engine
    """
    async with engine.begin() as conn:
        await conn.run_sync(TasksBase.metadata.drop_all)
