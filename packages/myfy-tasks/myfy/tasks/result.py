"""
Task result types for result retrieval.

Provides TaskResult[T] for typed result access.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

from .models import TaskStatus

T = TypeVar("T")


@dataclass
class TaskResult(Generic[T]):
    """
    Result of a task execution.

    Provides access to task status, return value, errors, and progress.

    Example:
        ```python
        task_id = await send_email.send(to="user@example.com", ...)

        # Later, check result
        result = await send_email.get_result(task_id)

        if result.status == TaskStatus.COMPLETED:
            print(f"Result: {result.value}")
        elif result.status == TaskStatus.FAILED:
            print(f"Error: {result.error}")
        elif result.status == TaskStatus.RUNNING:
            print(f"Progress: {result.progress}")
        ```

    Type Parameters:
        T: The return type of the task function
    """

    task_id: str
    """Unique task identifier."""

    status: TaskStatus
    """Current task status (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)."""

    value: T | None = None
    """Return value if task completed successfully."""

    error: str | None = None
    """Error message if task failed."""

    traceback: str | None = None
    """Full traceback if task failed."""

    started_at: datetime | None = None
    """When the task started executing."""

    completed_at: datetime | None = None
    """When the task finished (success or failure)."""

    progress: tuple[int, int] | None = None
    """Current progress as (current, total) if reported."""

    progress_message: str | None = None
    """Optional progress message."""

    attempt: int = 1
    """Current retry attempt (1-based)."""

    @property
    def is_pending(self) -> bool:
        """Check if task is waiting to be executed."""
        return self.status == TaskStatus.PENDING

    @property
    def is_running(self) -> bool:
        """Check if task is currently executing."""
        return self.status == TaskStatus.RUNNING

    @property
    def is_completed(self) -> bool:
        """Check if task completed successfully."""
        return self.status == TaskStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if task failed."""
        return self.status == TaskStatus.FAILED

    @property
    def is_cancelled(self) -> bool:
        """Check if task was cancelled."""
        return self.status == TaskStatus.CANCELLED

    @property
    def is_finished(self) -> bool:
        """Check if task is no longer running (completed, failed, or cancelled)."""
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        )

    @property
    def progress_percent(self) -> float | None:
        """Get progress as percentage (0-100) if available."""
        if self.progress is None:
            return None
        current, total = self.progress
        if total == 0:
            return 100.0
        return (current / total) * 100
