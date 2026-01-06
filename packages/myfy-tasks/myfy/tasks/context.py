"""
Task context for progress reporting and metadata.

Provides TaskContext that is auto-injected into tasks for progress updates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .queue import TaskQueue


@dataclass
class TaskContext:
    """
    Context available to tasks for progress and metadata.

    TaskContext is automatically injected when a task declares it as a parameter.
    It provides methods to report progress and check for cancellation.

    Example:
        ```python
        @task
        async def process_batch(
            items: list[str],
            ctx: TaskContext,
        ) -> int:
            for i, item in enumerate(items):
                await process_item(item)
                await ctx.update_progress(current=i + 1, total=len(items))
            return len(items)
        ```

    Attributes:
        task_id: Unique identifier for this task execution
        attempt: Current retry attempt (1-based, starts at 1)
    """

    task_id: str
    attempt: int = 1

    # Internal references (not exposed to users)
    _queue: TaskQueue | None = field(default=None, repr=False)
    _session_factory: Any = field(default=None, repr=False)
    _cancelled: bool = field(default=False, repr=False)

    async def update_progress(
        self,
        current: int,
        total: int,
        message: str | None = None,
    ) -> None:
        """
        Report task progress.

        Progress is stored in the database and can be queried via get_result().

        Args:
            current: Current progress value (e.g., items processed)
            total: Total expected value (e.g., total items)
            message: Optional progress message (max 255 chars)

        Example:
            ```python
            for i, item in enumerate(items):
                await process_item(item)
                await ctx.update_progress(
                    current=i + 1,
                    total=len(items),
                    message=f"Processing {item}",
                )
            ```
        """
        if self._queue is None or self._session_factory is None:
            return

        async with self._session_factory.session_context() as session:
            await self._queue.update_progress(
                session,
                task_id=self.task_id,
                current=current,
                total=total,
                message=message,
            )

    def is_cancelled(self) -> bool:
        """
        Check if the task has been cancelled/revoked.

        Use this in long-running tasks to check for cancellation requests.
        When cancelled, you should clean up and return early.

        Returns:
            True if the task should stop execution

        Example:
            ```python
            for item in items:
                if ctx.is_cancelled():
                    return  # Clean exit
                await process_item(item)
            ```
        """
        return self._cancelled

    def _set_cancelled(self) -> None:
        """Mark the task as cancelled (internal use)."""
        self._cancelled = True
