"""
Task registry for storing task definitions.

Provides a singleton registry for all registered tasks.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .errors import TaskAlreadyRegisteredError, TaskNotFoundError

if TYPE_CHECKING:
    from .task import Task

logger = logging.getLogger(__name__)


class TaskRegistry:
    """
    Global registry of task definitions.

    The registry is a singleton that stores all tasks decorated with @task.
    Workers use this registry to look up task implementations by name.

    Example:
        ```python
        registry = TaskRegistry.get_instance()

        # Get a task by name
        task = registry.get("myapp.tasks.send_email")

        # List all tasks
        for name, task in registry.get_all().items():
            print(f"{name}: {task}")
        ```
    """

    _instance: TaskRegistry | None = None

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    @classmethod
    def get_instance(cls) -> TaskRegistry:
        """
        Get the singleton registry instance.

        Returns:
            The global TaskRegistry instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance (for testing).

        Warning: This clears all registered tasks.
        """
        cls._instance = None

    def register(self, task: Task) -> None:
        """
        Register a task definition.

        Args:
            task: The task to register

        Raises:
            TaskAlreadyRegisteredError: If a task with this name already exists
        """
        if task.name in self._tasks:
            raise TaskAlreadyRegisteredError(task.name)

        self._tasks[task.name] = task
        logger.debug(f"Registered task: {task.name}")

    def get(self, name: str) -> Task:
        """
        Get a task definition by name.

        Args:
            name: The fully qualified task name

        Returns:
            The task definition

        Raises:
            TaskNotFoundError: If the task is not registered
        """
        task = self._tasks.get(name)
        if task is None:
            raise TaskNotFoundError(name)
        return task

    def get_or_none(self, name: str) -> Task | None:
        """
        Get a task definition by name, or None if not found.

        Args:
            name: The fully qualified task name

        Returns:
            The task definition, or None if not registered
        """
        return self._tasks.get(name)

    def get_all(self) -> dict[str, Task]:
        """
        Get all registered tasks.

        Returns:
            Dictionary mapping task names to task definitions
        """
        return self._tasks.copy()

    def clear(self) -> None:
        """
        Clear all registered tasks (for testing).

        Warning: This removes all tasks from the registry.
        """
        self._tasks.clear()
        logger.debug("Cleared task registry")

    def __len__(self) -> int:
        """Return the number of registered tasks."""
        return len(self._tasks)

    def __contains__(self, name: str) -> bool:
        """Check if a task is registered."""
        return name in self._tasks
