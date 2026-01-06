"""
Tasks module for myfy.

Provides asynchronous task processing with SQL-based queue.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from myfy.core.config import load_settings
from myfy.core.di import SINGLETON
from myfy.data import DataModule

from .config import TasksSettings
from .errors import TasksModuleNotConfiguredError
from .extensions import ITaskProvider
from .models import TasksBase
from .queue import TaskQueue
from .registry import TaskRegistry
from .task import _set_module_refs

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

    from myfy.core.di import Container
    from myfy.data import SessionFactory

logger = logging.getLogger(__name__)


class TasksModule:
    """
    Tasks module - provides async task processing.

    Features:
    - SQL-based task queue (works with any database)
    - @task decorator for defining tasks
    - TASK-scoped dependency injection
    - Configurable workers with concurrency control
    - Automatic retries with delay
    - Progress tracking via TaskContext

    Lifecycle (per ADR-0005):
    - configure(): Register services in DI container
    - extend(): No-op
    - finalize(): Set up module references for task dispatch
    - start(): Create tasks table if auto_create_tables=True
    - stop(): No-op (workers handle their own shutdown)

    Example:
        ```python
        from myfy.core import Application
        from myfy.data import DataModule
        from myfy.tasks import TasksModule

        app = Application()
        app.add_module(DataModule())
        app.add_module(TasksModule(auto_create_tables=True))
        ```
    """

    def __init__(
        self,
        settings: TasksSettings | None = None,
        auto_create_tables: bool = False,
    ) -> None:
        """
        Create tasks module.

        Args:
            settings: Custom tasks settings (defaults to loading from environment)
            auto_create_tables: If True, automatically create the tasks table
                during start(). Only recommended for development/test.
        """
        self._settings = settings
        self._auto_create_tables = auto_create_tables
        self._queue: TaskQueue | None = None
        self._engine: AsyncEngine | None = None
        self._session_factory: SessionFactory | None = None

    @property
    def name(self) -> str:
        """Module name for registration."""
        return "tasks"

    @property
    def requires(self) -> list[type]:
        """
        Module types this module depends on.

        TasksModule requires DataModule for database access.
        """
        return [DataModule]

    @property
    def provides(self) -> list[type]:
        """
        Extension protocols provided by this module.

        Implements ITaskProvider for task queue access.
        """
        return [ITaskProvider]

    def configure(self, container: Container) -> None:
        """
        Configure tasks module.

        Registers TasksSettings, TaskQueue, and TaskRegistry in the DI container.

        Note: In nested settings pattern (ADR-0007), TasksSettings may be
        registered by Application. Otherwise, load standalone TasksSettings.
        """
        from myfy.core.di.types import ProviderKey

        logger.debug("Configuring TasksModule...")

        # Check if TasksSettings already registered (from nested app settings)
        key = ProviderKey(TasksSettings)
        if key not in container._providers:
            if self._settings is None:
                self._settings = load_settings(TasksSettings)
            container.register(
                type_=TasksSettings,
                factory=lambda: self._settings,
                scope=SINGLETON,
            )
            logger.debug("Registered standalone TasksSettings")
        else:
            logger.debug("Using nested TasksSettings from application")

        # Get settings
        settings = self._settings or container.get(TasksSettings)

        # Create queue
        self._queue = TaskQueue(settings)

        # Register queue as singleton
        container.register(
            type_=TaskQueue,
            factory=lambda: self._queue,
            scope=SINGLETON,
        )

        # Register registry as singleton
        container.register(
            type_=TaskRegistry,
            factory=TaskRegistry.get_instance,
            scope=SINGLETON,
        )

        logger.debug("TasksModule configured successfully")

    def extend(self, container: Container) -> None:
        """
        Extend other modules' services (no-op for tasks).

        TasksModule doesn't need to extend other modules' services.
        This method exists for ADR-0005 lifecycle compliance.
        """

    def finalize(self, container: Container) -> None:
        """
        Finalize module configuration after container compilation.

        Sets up module-level references for task dispatch.
        """
        from sqlalchemy.ext.asyncio import AsyncEngine

        from myfy.data import SessionFactory

        # Get session factory for task dispatch
        self._session_factory = container.get(SessionFactory)
        self._engine = container.get(AsyncEngine)

        # Set module references for Task.send()
        if self._queue is not None and self._session_factory is not None:
            _set_module_refs(self._queue, self._session_factory)

        logger.debug("TasksModule finalized")

    async def start(self) -> None:
        """
        Start tasks module.

        Creates the tasks table if auto_create_tables is enabled.
        """
        if self._engine is None:
            raise TasksModuleNotConfiguredError("Engine")

        # Auto-create tables if enabled
        if self._auto_create_tables:
            await self._create_tables()

        logger.info("Tasks module started")

    async def _create_tables(self) -> None:
        """Create tasks table."""
        logger.info("Creating tasks table...")
        assert self._engine is not None

        async with self._engine.begin() as conn:
            await conn.run_sync(TasksBase.metadata.create_all)

        logger.info("Tasks table created")

    async def stop(self) -> None:
        """
        Stop tasks module (no-op).

        Workers handle their own shutdown via SIGTERM/SIGINT.
        """

    # ITaskProvider implementation

    def get_queue(self) -> TaskQueue:
        """
        Get the task queue.

        Returns:
            TaskQueue instance for enqueueing tasks

        Raises:
            TasksModuleNotConfiguredError: If queue not initialized
        """
        if self._queue is None:
            raise TasksModuleNotConfiguredError("TaskQueue")
        return self._queue

    def get_registry(self) -> TaskRegistry:
        """
        Get the task registry.

        Returns:
            TaskRegistry singleton containing all registered tasks
        """
        return TaskRegistry.get_instance()

    def __repr__(self) -> str:
        """String representation of module."""
        return f"TasksModule(auto_create_tables={self._auto_create_tables})"


# Module instance for entry point
tasks_module = TasksModule()
