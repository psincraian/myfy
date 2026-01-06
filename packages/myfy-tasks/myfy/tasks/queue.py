"""
SQL-based task queue operations.

Provides TaskQueue for enqueueing, claiming, and managing tasks.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import CursorResult, and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import TaskRecord, TaskStatus


def _utc_now() -> datetime:
    """Return current UTC time as naive datetime for database compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


if TYPE_CHECKING:
    from .config import TasksSettings

logger = logging.getLogger(__name__)


class TaskQueue:
    """
    SQL-based task queue operations.

    Handles all database operations for the task queue:
    - Enqueue: Add tasks to the queue
    - Claim: Workers claim pending tasks for execution
    - Complete/Fail: Update task status after execution
    - Progress: Update task progress
    - Reclaim: Reset stale tasks for retry
    """

    def __init__(self, settings: TasksSettings) -> None:
        """
        Initialize task queue.

        Args:
            settings: Task module settings
        """
        self._settings = settings

    async def enqueue(
        self,
        session: AsyncSession,
        *,
        name: str,
        args: dict[str, Any],
        priority: int = 0,
        max_retries: int | None = None,
        delay_seconds: float = 0,
    ) -> str:
        """
        Add a task to the queue.

        Args:
            session: Database session
            name: Task name (fully qualified)
            args: Task arguments (must be JSON-serializable)
            priority: Higher priority tasks execute first
            max_retries: Override default max retries
            delay_seconds: Delay before task becomes eligible

        Returns:
            task_id: Unique identifier for the task
        """
        task_id = str(uuid.uuid4())
        now = _utc_now()

        scheduled_at = now
        if delay_seconds > 0:
            scheduled_at = now + timedelta(seconds=delay_seconds)

        task = TaskRecord(
            id=task_id,
            name=name,
            args=args,
            status=TaskStatus.PENDING.value,
            priority=priority,
            max_retries=max_retries
            if max_retries is not None
            else self._settings.default_max_retries,
            scheduled_at=scheduled_at,
            created_at=now,
            updated_at=now,
        )

        session.add(task)
        await session.commit()

        logger.debug(f"Enqueued task {name} (id={task_id})")
        return task_id

    async def claim_tasks(
        self,
        session: AsyncSession,
        worker_id: str,
        batch_size: int | None = None,
    ) -> list[TaskRecord]:
        """
        Claim pending tasks for processing.

        Uses SELECT FOR UPDATE SKIP LOCKED to prevent race conditions
        when multiple workers poll simultaneously.

        Args:
            session: Database session
            worker_id: Unique identifier for the claiming worker
            batch_size: Number of tasks to claim (default from settings)

        Returns:
            List of claimed TaskRecord objects
        """
        batch_size = batch_size or self._settings.claim_batch_size
        now = _utc_now()

        # Find pending tasks that are ready to execute
        stmt = (
            select(TaskRecord)
            .where(
                and_(
                    TaskRecord.status == TaskStatus.PENDING.value,
                    TaskRecord.scheduled_at <= now,
                )
            )
            .order_by(TaskRecord.priority.desc(), TaskRecord.scheduled_at)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )

        result = await session.execute(stmt)
        tasks = list(result.scalars().all())

        if not tasks:
            return []

        # Claim the tasks
        task_ids = [t.id for t in tasks]
        update_stmt = (
            update(TaskRecord)
            .where(TaskRecord.id.in_(task_ids))
            .values(
                status=TaskStatus.RUNNING.value,
                worker_id=worker_id,
                started_at=now,
                updated_at=now,
            )
        )
        await session.execute(update_stmt)
        await session.commit()

        # Refresh to get updated values
        for task in tasks:
            task.status = TaskStatus.RUNNING.value
            task.worker_id = worker_id
            task.started_at = now

        logger.debug(f"Worker {worker_id} claimed {len(tasks)} task(s)")
        return tasks

    async def complete_task(
        self,
        session: AsyncSession,
        task_id: str,
        result: Any = None,
    ) -> None:
        """
        Mark a task as completed successfully.

        Args:
            session: Database session
            task_id: Task identifier
            result: Return value to store (must be JSON-serializable)
        """
        now = _utc_now()

        stmt = (
            update(TaskRecord)
            .where(TaskRecord.id == task_id)
            .values(
                status=TaskStatus.COMPLETED.value,
                completed_at=now,
                result=result,
                updated_at=now,
            )
        )
        await session.execute(stmt)
        await session.commit()

        logger.debug(f"Task {task_id} completed")

    async def fail_task(
        self,
        session: AsyncSession,
        task_id: str,
        error_message: str,
        error_traceback: str | None = None,
    ) -> bool:
        """
        Mark a task as failed and schedule retry if possible.

        Args:
            session: Database session
            task_id: Task identifier
            error_message: Error description
            error_traceback: Full traceback (optional)

        Returns:
            True if task will be retried, False if max retries exceeded
        """
        # Get current task state
        stmt = select(TaskRecord).where(TaskRecord.id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

        if task is None:
            logger.warning(f"Task {task_id} not found for failure update")
            return False

        now = _utc_now()

        if task.retry_count < task.max_retries:
            # Schedule retry
            retry_at = now + timedelta(seconds=self._settings.retry_delay_seconds)
            update_stmt = (
                update(TaskRecord)
                .where(TaskRecord.id == task_id)
                .values(
                    status=TaskStatus.PENDING.value,
                    retry_count=task.retry_count + 1,
                    scheduled_at=retry_at,
                    worker_id=None,
                    started_at=None,
                    error_message=error_message,
                    error_traceback=error_traceback,
                    updated_at=now,
                )
            )
            await session.execute(update_stmt)
            await session.commit()

            logger.info(
                f"Task {task_id} failed, scheduled retry {task.retry_count + 1}/{task.max_retries}"
            )
            return True
        # Max retries exceeded
        update_stmt = (
            update(TaskRecord)
            .where(TaskRecord.id == task_id)
            .values(
                status=TaskStatus.FAILED.value,
                completed_at=now,
                error_message=error_message,
                error_traceback=error_traceback,
                updated_at=now,
            )
        )
        await session.execute(update_stmt)
        await session.commit()

        logger.warning(f"Task {task_id} failed permanently after {task.max_retries} retries")
        return False

    async def cancel_task(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> bool:
        """
        Cancel a pending or running task.

        Args:
            session: Database session
            task_id: Task identifier

        Returns:
            True if task was cancelled, False if already finished
        """
        now = _utc_now()

        stmt = (
            update(TaskRecord)
            .where(
                and_(
                    TaskRecord.id == task_id,
                    TaskRecord.status.in_([TaskStatus.PENDING.value, TaskStatus.RUNNING.value]),
                )
            )
            .values(
                status=TaskStatus.CANCELLED.value,
                completed_at=now,
                updated_at=now,
            )
        )
        result = await session.execute(stmt)
        await session.commit()

        cancelled = cast("CursorResult[Any]", result).rowcount > 0
        if cancelled:
            logger.info(f"Task {task_id} cancelled")
        return cancelled

    async def update_progress(
        self,
        session: AsyncSession,
        task_id: str,
        current: int,
        total: int,
        message: str | None = None,
    ) -> None:
        """
        Update task progress.

        Args:
            session: Database session
            task_id: Task identifier
            current: Current progress value
            total: Total expected value
            message: Optional progress message
        """
        stmt = (
            update(TaskRecord)
            .where(TaskRecord.id == task_id)
            .values(
                progress_current=current,
                progress_total=total,
                progress_message=message[:255] if message else None,
                updated_at=_utc_now(),
            )
        )
        await session.execute(stmt)
        await session.commit()

    async def get_task(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> TaskRecord | None:
        """
        Get a task by ID.

        Args:
            session: Database session
            task_id: Task identifier

        Returns:
            TaskRecord or None if not found
        """
        stmt = select(TaskRecord).where(TaskRecord.id == task_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def reclaim_stale_tasks(
        self,
        session: AsyncSession,
    ) -> int:
        """
        Reset stale running tasks back to pending.

        Tasks that have been running longer than stale_task_timeout
        are assumed to be from crashed workers and reset for retry.

        Args:
            session: Database session

        Returns:
            Number of tasks reclaimed
        """
        stale_cutoff = _utc_now() - timedelta(seconds=self._settings.stale_task_timeout)

        stmt = (
            update(TaskRecord)
            .where(
                and_(
                    TaskRecord.status == TaskStatus.RUNNING.value,
                    TaskRecord.started_at < stale_cutoff,
                )
            )
            .values(
                status=TaskStatus.PENDING.value,
                worker_id=None,
                started_at=None,
                updated_at=_utc_now(),
            )
        )
        result = await session.execute(stmt)
        await session.commit()

        count = cast("CursorResult[Any]", result).rowcount
        if count > 0:
            logger.info(f"Reclaimed {count} stale task(s)")
        return count

    async def get_stats(
        self,
        session: AsyncSession,
    ) -> dict[str, int]:
        """
        Get task queue statistics.

        Args:
            session: Database session

        Returns:
            Dictionary with counts by status
        """
        from sqlalchemy import func

        stats = {}
        for status in TaskStatus:
            stmt = (
                select(func.count())
                .select_from(TaskRecord)
                .where(TaskRecord.status == status.value)
            )
            result = await session.execute(stmt)
            stats[status.value] = result.scalar() or 0

        return stats
