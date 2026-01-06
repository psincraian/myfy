"""
Task module exceptions.

Provides clear error messages for task-related failures.
"""

from __future__ import annotations


class TaskError(Exception):
    """Base exception for all task-related errors."""


class TaskNotFoundError(TaskError):
    """Raised when a task is not found in the registry."""

    def __init__(self, task_name: str) -> None:
        super().__init__(
            f"Task '{task_name}' not found. "
            "Ensure the task is decorated with @task and the module is imported."
        )
        self.task_name = task_name


class TaskSerializationError(TaskError):
    """Raised when task arguments cannot be serialized to JSON."""

    def __init__(self, task_name: str, cause: Exception) -> None:
        super().__init__(f"Failed to serialize arguments for task '{task_name}': {cause}")
        self.task_name = task_name
        self.__cause__ = cause


class TaskExecutionError(TaskError):
    """Raised when task execution fails."""

    def __init__(self, task_id: str, task_name: str, cause: Exception) -> None:
        super().__init__(f"Task {task_name} (id={task_id}) failed: {cause}")
        self.task_id = task_id
        self.task_name = task_name
        self.__cause__ = cause


class TaskTimeoutError(TaskError):
    """Raised when task execution exceeds the configured timeout."""

    def __init__(self, task_id: str, task_name: str, timeout: float) -> None:
        super().__init__(f"Task {task_name} (id={task_id}) exceeded timeout of {timeout} seconds")
        self.task_id = task_id
        self.task_name = task_name
        self.timeout = timeout


class TaskCancelledError(TaskError):
    """Raised when a task is cancelled/revoked."""

    def __init__(self, task_id: str, task_name: str) -> None:
        super().__init__(f"Task {task_name} (id={task_id}) was cancelled")
        self.task_id = task_id
        self.task_name = task_name


class TasksModuleNotConfiguredError(TaskError):
    """Raised when module operations are called before configure()."""

    def __init__(self, resource: str) -> None:
        super().__init__(
            f"{resource} not initialized. "
            "Ensure TasksModule.configure() was called during application initialization."
        )
        self.resource = resource


class TaskAlreadyRegisteredError(TaskError):
    """Raised when attempting to register a task with a name that already exists."""

    def __init__(self, task_name: str) -> None:
        super().__init__(
            f"Task '{task_name}' is already registered. "
            "Use a unique name or check for duplicate @task decorators."
        )
        self.task_name = task_name
