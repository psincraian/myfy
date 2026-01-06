"""Unit tests for TaskQueue."""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import update

from myfy.tasks.config import TasksSettings
from myfy.tasks.models import TaskRecord, TasksBase, TaskStatus
from myfy.tasks.queue import TaskQueue


def _utc_now() -> datetime:
    """Return current UTC time as naive datetime for database compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


@pytest_asyncio.fixture
async def queue_with_db(test_db):
    """Create a TaskQueue with test database."""
    data_module, session_factory = test_db

    # Create tasks table
    engine = data_module.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(TasksBase.metadata.create_all)

    settings = TasksSettings()
    queue = TaskQueue(settings)

    yield queue, session_factory

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(TasksBase.metadata.drop_all)


@pytest.mark.asyncio
async def test_enqueue_task(queue_with_db):
    """Test enqueueing a task."""
    queue, session_factory = queue_with_db

    async with session_factory.session_context() as session:
        task_id = await queue.enqueue(
            session,
            name="test.task",
            args={"x": 1, "y": 2},
            priority=5,
        )

    assert task_id is not None

    # Verify task was created
    async with session_factory.session_context() as session:
        task = await queue.get_task(session, task_id)

    assert task is not None
    assert task.name == "test.task"
    assert task.args == {"x": 1, "y": 2}
    assert task.priority == 5
    assert task.status == TaskStatus.PENDING.value


@pytest.mark.asyncio
async def test_enqueue_with_delay(queue_with_db):
    """Test enqueueing a task with delay."""
    queue, session_factory = queue_with_db

    async with session_factory.session_context() as session:
        task_id = await queue.enqueue(
            session,
            name="delayed.task",
            args={},
            delay_seconds=60,
        )

    async with session_factory.session_context() as session:
        task = await queue.get_task(session, task_id)

    # Should be scheduled in the future
    assert task.scheduled_at > _utc_now()


@pytest.mark.asyncio
async def test_claim_tasks(queue_with_db):
    """Test claiming tasks from queue."""
    queue, session_factory = queue_with_db

    # Enqueue tasks
    async with session_factory.session_context() as session:
        await queue.enqueue(session, name="task1", args={})
        await queue.enqueue(session, name="task2", args={})
        await queue.enqueue(session, name="task3", args={})

    # Claim tasks
    async with session_factory.session_context() as session:
        claimed = await queue.claim_tasks(session, "worker-1", batch_size=2)

    assert len(claimed) == 2

    # Verify status changed
    for task in claimed:
        assert task.status == TaskStatus.RUNNING.value
        assert task.worker_id == "worker-1"
        assert task.started_at is not None


@pytest.mark.asyncio
async def test_claim_respects_priority(queue_with_db):
    """Test that higher priority tasks are claimed first."""
    queue, session_factory = queue_with_db

    # Enqueue tasks with different priorities
    async with session_factory.session_context() as session:
        await queue.enqueue(session, name="low", args={}, priority=1)
        await queue.enqueue(session, name="high", args={}, priority=10)
        await queue.enqueue(session, name="medium", args={}, priority=5)

    # Claim one task
    async with session_factory.session_context() as session:
        claimed = await queue.claim_tasks(session, "worker-1", batch_size=1)

    assert len(claimed) == 1
    assert claimed[0].name == "high"


@pytest.mark.asyncio
async def test_complete_task(queue_with_db):
    """Test completing a task."""
    queue, session_factory = queue_with_db

    # Enqueue and claim
    async with session_factory.session_context() as session:
        task_id = await queue.enqueue(session, name="task", args={})

    async with session_factory.session_context() as session:
        await queue.claim_tasks(session, "worker-1")

    # Complete
    async with session_factory.session_context() as session:
        await queue.complete_task(session, task_id, result={"success": True})

    # Verify
    async with session_factory.session_context() as session:
        task = await queue.get_task(session, task_id)

    assert task.status == TaskStatus.COMPLETED.value
    assert task.result == {"success": True}
    assert task.completed_at is not None


@pytest.mark.asyncio
async def test_fail_task_with_retry(queue_with_db):
    """Test failing a task that should be retried."""
    queue, session_factory = queue_with_db

    # Enqueue with retries
    async with session_factory.session_context() as session:
        task_id = await queue.enqueue(session, name="task", args={}, max_retries=3)

    async with session_factory.session_context() as session:
        await queue.claim_tasks(session, "worker-1")

    # Fail
    async with session_factory.session_context() as session:
        will_retry = await queue.fail_task(session, task_id, "Error occurred")

    assert will_retry is True

    # Verify task is pending again
    async with session_factory.session_context() as session:
        task = await queue.get_task(session, task_id)

    assert task.status == TaskStatus.PENDING.value
    assert task.retry_count == 1
    assert task.error_message == "Error occurred"


@pytest.mark.asyncio
async def test_fail_task_max_retries_exceeded(queue_with_db):
    """Test failing a task that has exceeded max retries."""
    queue, session_factory = queue_with_db

    # Enqueue with no retries
    async with session_factory.session_context() as session:
        task_id = await queue.enqueue(session, name="task", args={}, max_retries=0)

    async with session_factory.session_context() as session:
        await queue.claim_tasks(session, "worker-1")

    # Fail
    async with session_factory.session_context() as session:
        will_retry = await queue.fail_task(session, task_id, "Error")

    assert will_retry is False

    # Verify task is failed
    async with session_factory.session_context() as session:
        task = await queue.get_task(session, task_id)

    assert task.status == TaskStatus.FAILED.value


@pytest.mark.asyncio
async def test_cancel_task(queue_with_db):
    """Test cancelling a task."""
    queue, session_factory = queue_with_db

    async with session_factory.session_context() as session:
        task_id = await queue.enqueue(session, name="task", args={})

    async with session_factory.session_context() as session:
        cancelled = await queue.cancel_task(session, task_id)

    assert cancelled is True

    async with session_factory.session_context() as session:
        task = await queue.get_task(session, task_id)

    assert task.status == TaskStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_update_progress(queue_with_db):
    """Test updating task progress."""
    queue, session_factory = queue_with_db

    async with session_factory.session_context() as session:
        task_id = await queue.enqueue(session, name="task", args={})

    async with session_factory.session_context() as session:
        await queue.update_progress(
            session,
            task_id,
            current=50,
            total=100,
            message="Halfway done",
        )

    async with session_factory.session_context() as session:
        task = await queue.get_task(session, task_id)

    assert task.progress_current == 50
    assert task.progress_total == 100
    assert task.progress_message == "Halfway done"


@pytest.mark.asyncio
async def test_get_stats(queue_with_db):
    """Test getting queue statistics."""
    queue, session_factory = queue_with_db

    # Create tasks with different statuses
    async with session_factory.session_context() as session:
        await queue.enqueue(session, name="pending1", args={})
        await queue.enqueue(session, name="pending2", args={})

    async with session_factory.session_context() as session:
        stats = await queue.get_stats(session)

    assert stats["pending"] == 2
    assert stats["running"] == 0
    assert stats["completed"] == 0
    assert stats["failed"] == 0


@pytest_asyncio.fixture
async def queue_with_short_stale_timeout(test_db):
    """Create a TaskQueue with short stale timeout for testing."""
    data_module, session_factory = test_db

    # Create tasks table
    engine = data_module.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(TasksBase.metadata.create_all)

    # Use short stale timeout (minimum is 60 seconds)
    settings = TasksSettings(stale_task_timeout=60.0)
    queue = TaskQueue(settings)

    yield queue, session_factory

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(TasksBase.metadata.drop_all)


@pytest.mark.asyncio
async def test_reclaim_stale_tasks(queue_with_short_stale_timeout):
    """Test reclaiming tasks from crashed workers.

    This simulates a scenario where a worker claims tasks but crashes
    before completing them. The reclaim_stale_tasks() method should
    reset these tasks back to PENDING so they can be picked up by
    another worker.
    """
    queue, session_factory = queue_with_short_stale_timeout

    # Enqueue a task
    async with session_factory.session_context() as session:
        task_id = await queue.enqueue(session, name="stale.task", args={})

    # Claim it (simulating a worker picking it up)
    async with session_factory.session_context() as session:
        claimed = await queue.claim_tasks(session, "crashed-worker")
    assert len(claimed) == 1

    # Verify it's now RUNNING
    async with session_factory.session_context() as session:
        task = await queue.get_task(session, task_id)
    assert task.status == TaskStatus.RUNNING.value
    assert task.worker_id == "crashed-worker"

    # Simulate time passing by backdating started_at to make it "stale"
    # The stale_task_timeout is 60 seconds for this test
    stale_time = _utc_now() - timedelta(seconds=120)  # 120 seconds ago (> 60s threshold)
    async with session_factory.session_context() as session:
        stmt = update(TaskRecord).where(TaskRecord.id == task_id).values(started_at=stale_time)
        await session.execute(stmt)
        await session.commit()

    # Reclaim stale tasks
    async with session_factory.session_context() as session:
        reclaimed_count = await queue.reclaim_stale_tasks(session)

    assert reclaimed_count == 1

    # Verify task is back to PENDING
    async with session_factory.session_context() as session:
        task = await queue.get_task(session, task_id)

    assert task.status == TaskStatus.PENDING.value
    assert task.worker_id is None
    assert task.started_at is None


@pytest.mark.asyncio
async def test_reclaim_stale_tasks_does_not_affect_recent_tasks(queue_with_short_stale_timeout):
    """Test that reclaim_stale_tasks() does not affect recently claimed tasks."""
    queue, session_factory = queue_with_short_stale_timeout

    # Enqueue and claim a task
    async with session_factory.session_context() as session:
        task_id = await queue.enqueue(session, name="fresh.task", args={})

    async with session_factory.session_context() as session:
        await queue.claim_tasks(session, "active-worker")

    # Don't backdate - this is a fresh task

    # Try to reclaim
    async with session_factory.session_context() as session:
        reclaimed_count = await queue.reclaim_stale_tasks(session)

    assert reclaimed_count == 0

    # Task should still be RUNNING
    async with session_factory.session_context() as session:
        task = await queue.get_task(session, task_id)

    assert task.status == TaskStatus.RUNNING.value
    assert task.worker_id == "active-worker"
