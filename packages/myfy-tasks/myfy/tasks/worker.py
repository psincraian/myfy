"""
Task worker for processing tasks from the queue.

Provides TaskWorker that polls the database and executes tasks.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import traceback
import uuid
from typing import TYPE_CHECKING, Any

from myfy.core.di import ScopeContext

from .context import TaskContext
from .errors import TaskNotFoundError
from .models import TaskRecord, TaskStatus
from .registry import TaskRegistry

if TYPE_CHECKING:
    from myfy.core.di import Container
    from myfy.data import SessionFactory

    from .config import TasksSettings
    from .queue import TaskQueue

logger = logging.getLogger(__name__)


class TaskWorker:
    """
    Worker that processes tasks from the queue.

    The worker polls the database for pending tasks, claims them,
    and executes them with proper TASK scope management.

    Features:
    - Configurable concurrency (multiple tasks in parallel)
    - Automatic retries on failure
    - Graceful shutdown on SIGTERM/SIGINT
    - TASK scope for dependency injection
    - TaskContext injection for progress reporting

    Example:
        ```python
        worker = TaskWorker(
            container=app.container,
            settings=tasks_settings,
            queue=task_queue,
            session_factory=session_factory,
        )
        await worker.run()
        ```
    """

    def __init__(
        self,
        *,
        container: Container,
        settings: TasksSettings,
        queue: TaskQueue,
        session_factory: SessionFactory,
        worker_id: str | None = None,
    ) -> None:
        """
        Initialize task worker.

        Args:
            container: DI container for resolving dependencies
            settings: Task module settings
            queue: Task queue for claiming tasks
            session_factory: Session factory for database access
            worker_id: Unique worker identifier (auto-generated if not set)
        """
        self._container = container
        self._settings = settings
        self._queue = queue
        self._session_factory = session_factory
        self._worker_id = worker_id or settings.worker_id or str(uuid.uuid4())[:8]

        self._running = False
        self._shutdown_event = asyncio.Event()
        self._active_tasks: set[asyncio.Task] = set()
        self._semaphore = asyncio.Semaphore(settings.worker_concurrency)

    @property
    def worker_id(self) -> str:
        """Unique worker identifier."""
        return self._worker_id

    @property
    def is_running(self) -> bool:
        """Whether the worker is currently running."""
        return self._running

    def setup_signal_handlers(self) -> None:
        """
        Setup signal handlers for graceful shutdown.

        Handles SIGTERM and SIGINT to trigger graceful shutdown.
        """
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_shutdown_signal)

    def _handle_shutdown_signal(self) -> None:
        """Handle shutdown signal."""
        logger.info(f"Worker {self._worker_id} received shutdown signal")
        self._shutdown_event.set()

    async def run(self) -> None:
        """
        Main worker loop.

        Polls for tasks and processes them until shutdown signal received.
        """
        self._running = True
        logger.info(
            f"Worker {self._worker_id} starting "
            f"(concurrency={self._settings.worker_concurrency}, "
            f"poll_interval={self._settings.poll_interval}s)"
        )

        try:
            while not self._shutdown_event.is_set():
                try:
                    await self._poll_and_process()
                except Exception as e:
                    logger.exception(f"Error in worker loop: {e}")
                    await asyncio.sleep(self._settings.poll_interval)
        finally:
            await self._shutdown()

    async def _poll_and_process(self) -> None:
        """Poll for tasks and process them."""
        # Claim tasks from queue
        async with self._session_factory.session_context() as session:
            tasks = await self._queue.claim_tasks(session, self._worker_id)

        if not tasks:
            await asyncio.sleep(self._settings.poll_interval)
            return

        logger.debug(f"Worker {self._worker_id} claimed {len(tasks)} task(s)")

        # Process tasks concurrently (up to concurrency limit)
        for task_record in tasks:
            async with self._semaphore:
                asyncio_task = asyncio.create_task(self._execute_task(task_record))
                self._active_tasks.add(asyncio_task)
                asyncio_task.add_done_callback(self._active_tasks.discard)

    async def _execute_task(self, task_record: TaskRecord) -> None:
        """
        Execute a single task with proper scope management.

        Args:
            task_record: The task record from the database
        """
        task_id = task_record.id
        task_name = task_record.name

        logger.info(
            f"Executing task {task_name} (id={task_id}, attempt={task_record.retry_count + 1})"
        )

        # Get task definition from registry
        registry = TaskRegistry.get_instance()
        try:
            task_def = registry.get(task_name)
        except TaskNotFoundError:
            error_msg = f"Task '{task_name}' not found in registry"
            logger.error(error_msg)
            async with self._session_factory.session_context() as session:
                await self._queue.fail_task(session, task_id, error_msg)
            return

        # Initialize TASK scope for this execution
        ScopeContext.init_task_scope()

        try:
            # Build kwargs from stored args
            kwargs: dict[str, Any] = dict(task_record.args)

            # Inject TaskContext if task accepts it
            if task_def.has_context:
                ctx = TaskContext(
                    task_id=task_id,
                    attempt=task_record.retry_count + 1,
                    _queue=self._queue,
                    _session_factory=self._session_factory,
                )
                kwargs["ctx"] = ctx

            # Resolve injectable dependencies from DI container
            for param_name, param_type in task_def.injectable_params.items():
                if param_name not in kwargs:
                    try:
                        kwargs[param_name] = self._container.get(param_type)
                    except Exception as e:
                        logger.warning(
                            f"Could not inject {param_name} ({param_type.__name__}): {e}. "
                            "Parameter must be provided as task argument."
                        )

            # Execute with timeout
            try:
                if task_def.is_async:
                    result = await asyncio.wait_for(
                        task_def.func(**kwargs),
                        timeout=self._settings.task_timeout,
                    )
                else:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(task_def.func, **kwargs),
                        timeout=self._settings.task_timeout,
                    )

                # Mark completed
                async with self._session_factory.session_context() as session:
                    await self._queue.complete_task(session, task_id, result)

                logger.info(f"Task {task_name} (id={task_id}) completed successfully")

            except TimeoutError:
                error_msg = f"Task exceeded timeout of {self._settings.task_timeout}s"
                logger.error(f"Task {task_name} (id={task_id}) timed out")
                async with self._session_factory.session_context() as session:
                    await self._queue.fail_task(session, task_id, error_msg)

        except Exception as e:
            # Task execution failed
            error_msg = str(e)
            error_tb = traceback.format_exc()
            logger.exception(f"Task {task_name} (id={task_id}) failed: {e}")

            # Check if exception type should trigger retry
            should_retry = True
            if task_def.retry_on:
                should_retry = any(isinstance(e, exc_type) for exc_type in task_def.retry_on)

            async with self._session_factory.session_context() as session:
                if should_retry:
                    will_retry = await self._queue.fail_task(session, task_id, error_msg, error_tb)
                    if will_retry:
                        logger.info(f"Task {task_name} (id={task_id}) scheduled for retry")
                else:
                    # Force failure without retry
                    from datetime import UTC, datetime

                    from sqlalchemy import update

                    stmt = (
                        update(TaskRecord)
                        .where(TaskRecord.id == task_id)
                        .values(
                            status=TaskStatus.FAILED.value,
                            completed_at=datetime.now(UTC),
                            error_message=error_msg,
                            error_traceback=error_tb,
                        )
                    )
                    await session.execute(stmt)
                    await session.commit()
                    logger.warning(
                        f"Task {task_name} (id={task_id}) failed (no retry for {type(e).__name__})"
                    )

        finally:
            # Clear TASK scope
            ScopeContext.clear_task_bag()

    async def _shutdown(self) -> None:
        """Graceful shutdown - wait for active tasks."""
        self._running = False

        if self._active_tasks:
            logger.info(
                f"Worker {self._worker_id} waiting for "
                f"{len(self._active_tasks)} active task(s) to complete..."
            )
            # Wait for active tasks with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._active_tasks, return_exceptions=True),
                    timeout=self._settings.task_timeout,
                )
            except TimeoutError:
                logger.warning(
                    f"Worker {self._worker_id} shutdown timed out, some tasks may be interrupted"
                )

        logger.info(f"Worker {self._worker_id} stopped")

    async def run_once(self) -> int:
        """
        Run a single poll cycle (for testing).

        Returns:
            Number of tasks processed
        """
        async with self._session_factory.session_context() as session:
            tasks = await self._queue.claim_tasks(session, self._worker_id)

        for task_record in tasks:
            await self._execute_task(task_record)

        return len(tasks)
