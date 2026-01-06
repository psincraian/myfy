"""Integration tests for TaskWorker."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine

from myfy.core.di import SINGLETON, Container
from myfy.tasks import TasksModule, TasksSettings, TaskStatus, task
from myfy.tasks.worker import TaskWorker


@pytest_asyncio.fixture
async def worker_env(test_db):
    """
    Fixture providing a complete environment for worker testing.

    Yields tuple of (module, queue, session_factory, container).
    """
    data_module, session_factory = test_db

    settings = TasksSettings(
        poll_interval=0.1,
        worker_concurrency=2,
        task_timeout=5.0,
    )
    module = TasksModule(settings=settings, auto_create_tables=True)

    container = Container()
    container.register(type(session_factory), lambda: session_factory, scope=SINGLETON)

    engine = session_factory._sessionmaker.kw.get("bind")
    if engine:
        container.register(AsyncEngine, lambda: engine, scope=SINGLETON)

    module.configure(container)
    container.compile()
    module.finalize(container)
    await module.start()

    try:
        yield module, module.get_queue(), session_factory, container
    finally:
        await module.stop()


class TestWorkerRunOnce:
    """Tests for TaskWorker.run_once() method."""

    @pytest.mark.asyncio
    async def test_worker_run_once_processes_task(self, worker_env):
        """Test that worker.run_once() processes a single batch of tasks."""
        module, queue, session_factory, container = worker_env

        @task
        async def simple_task(value: int) -> int:
            return value * 2

        # Enqueue a task
        task_id = await simple_task.send(value=5)

        # Create worker
        worker = TaskWorker(
            container=container,
            settings=module._settings,
            queue=queue,
            session_factory=session_factory,
            worker_id="test-worker",
        )

        # Run once
        processed = await worker.run_once()
        assert processed == 1

        # Verify task completed
        async with session_factory.session_context() as session:
            record = await queue.get_task(session, task_id)

        assert record.status == TaskStatus.COMPLETED.value
        assert record.result == 10

    @pytest.mark.asyncio
    async def test_worker_run_once_processes_multiple_tasks(self, worker_env):
        """Test that worker processes multiple tasks in one batch."""
        module, queue, session_factory, container = worker_env

        @task
        async def batch_task(n: int) -> int:
            return n

        # Enqueue multiple tasks
        for i in range(3):
            await batch_task.send(n=i)

        worker = TaskWorker(
            container=container,
            settings=module._settings,
            queue=queue,
            session_factory=session_factory,
        )

        # Run once - should process up to claim_batch_size
        processed = await worker.run_once()
        assert processed >= 1  # At least one batch claimed

    @pytest.mark.asyncio
    async def test_worker_run_once_returns_zero_when_empty(self, worker_env):
        """Test that worker.run_once() returns 0 when queue is empty."""
        module, queue, session_factory, container = worker_env

        worker = TaskWorker(
            container=container,
            settings=module._settings,
            queue=queue,
            session_factory=session_factory,
        )

        processed = await worker.run_once()
        assert processed == 0


class TestWorkerTaskExecution:
    """Tests for task execution within worker."""

    @pytest.mark.asyncio
    async def test_worker_handles_task_failure(self, worker_env):
        """Test that worker properly handles task failures."""
        module, queue, session_factory, container = worker_env

        @task(max_retries=0)
        async def failing_task() -> None:
            raise ValueError("Task failed intentionally")

        task_id = await failing_task.send()

        worker = TaskWorker(
            container=container,
            settings=module._settings,
            queue=queue,
            session_factory=session_factory,
        )

        await worker.run_once()

        async with session_factory.session_context() as session:
            record = await queue.get_task(session, task_id)

        assert record.status == TaskStatus.FAILED.value
        assert "Task failed intentionally" in record.error_message

    @pytest.mark.asyncio
    async def test_worker_schedules_retry_on_failure(self, worker_env):
        """Test that worker schedules retry for failed tasks with retries remaining."""
        module, queue, session_factory, container = worker_env

        @task(max_retries=2)
        async def fail_task() -> str:
            raise ValueError("Always fails")

        task_id = await fail_task.send()

        worker = TaskWorker(
            container=container,
            settings=module._settings,
            queue=queue,
            session_factory=session_factory,
        )

        # First attempt - fails, should schedule retry
        await worker.run_once()
        async with session_factory.session_context() as session:
            record = await queue.get_task(session, task_id)

        # Task should be pending (scheduled for retry) with retry_count incremented
        assert record.status == TaskStatus.PENDING.value
        assert record.retry_count == 1
        assert record.error_message is not None


class TestWorkerRetryOnFiltering:
    """Tests for retry_on exception filtering."""

    @pytest.mark.asyncio
    async def test_retry_on_matching_exception_triggers_retry(self, worker_env):
        """Test that exceptions in retry_on list trigger retry."""
        module, queue, session_factory, container = worker_env

        # Define custom exception
        class RetryableError(Exception):
            pass

        @task(max_retries=2, retry_on=[RetryableError])
        async def retry_on_specific() -> None:
            raise RetryableError("This should retry")

        task_id = await retry_on_specific.send()

        worker = TaskWorker(
            container=container,
            settings=module._settings,
            queue=queue,
            session_factory=session_factory,
        )

        await worker.run_once()

        async with session_factory.session_context() as session:
            record = await queue.get_task(session, task_id)

        # Should be pending (scheduled for retry)
        assert record.status == TaskStatus.PENDING.value
        assert record.retry_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_non_matching_exception_fails_immediately(self, worker_env):
        """Test that exceptions NOT in retry_on list fail immediately without retry."""
        module, queue, session_factory, container = worker_env

        # Define custom exceptions
        class RetryableError(Exception):
            pass

        class NonRetryableError(Exception):
            pass

        @task(max_retries=2, retry_on=[RetryableError])
        async def fail_with_wrong_error() -> None:
            raise NonRetryableError("This should NOT retry")

        task_id = await fail_with_wrong_error.send()

        worker = TaskWorker(
            container=container,
            settings=module._settings,
            queue=queue,
            session_factory=session_factory,
        )

        await worker.run_once()

        async with session_factory.session_context() as session:
            record = await queue.get_task(session, task_id)

        # Should be FAILED immediately (no retry)
        assert record.status == TaskStatus.FAILED.value
        assert record.retry_count == 0  # Never retried
        assert "should NOT retry" in record.error_message

    @pytest.mark.asyncio
    async def test_empty_retry_on_retries_all_exceptions(self, worker_env):
        """Test that empty retry_on (default) retries all exceptions."""
        module, queue, session_factory, container = worker_env

        @task(max_retries=2)  # No retry_on specified
        async def always_retry() -> None:
            raise ValueError("Any error should retry")

        task_id = await always_retry.send()

        worker = TaskWorker(
            container=container,
            settings=module._settings,
            queue=queue,
            session_factory=session_factory,
        )

        await worker.run_once()

        async with session_factory.session_context() as session:
            record = await queue.get_task(session, task_id)

        # Should be pending (scheduled for retry)
        assert record.status == TaskStatus.PENDING.value
        assert record.retry_count == 1


class TestWorkerDependencyInjection:
    """Tests for DI injection in worker task execution."""

    @pytest.mark.asyncio
    async def test_worker_injects_registered_dependency(self, test_db):
        """Test that worker injects DI dependencies into tasks."""
        from sqlalchemy.ext.asyncio import AsyncEngine

        data_module, session_factory = test_db

        # Define a service
        class GreetingService:
            def greet(self, name: str) -> str:
                return f"Hello, {name}!"

        greeting_service = GreetingService()

        # Create module and container with service registered BEFORE compile
        settings = TasksSettings(poll_interval=0.1, task_timeout=5.0)
        module = TasksModule(settings=settings, auto_create_tables=True)

        container = Container()
        container.register(type(session_factory), lambda: session_factory, scope=SINGLETON)

        engine = session_factory._sessionmaker.kw.get("bind")
        if engine:
            container.register(AsyncEngine, lambda: engine, scope=SINGLETON)

        # Register service BEFORE compile
        container.register(GreetingService, lambda: greeting_service, scope=SINGLETON)

        module.configure(container)
        container.compile()
        module.finalize(container)
        await module.start()

        try:

            @task
            async def greet_user(name: str, service: GreetingService) -> str:
                return service.greet(name)

            task_id = await greet_user.send(name="World")

            queue = module.get_queue()
            worker = TaskWorker(
                container=container,
                settings=settings,
                queue=queue,
                session_factory=session_factory,
            )

            await worker.run_once()

            async with session_factory.session_context() as session:
                record = await queue.get_task(session, task_id)

            assert record.status == TaskStatus.COMPLETED.value
            assert record.result == "Hello, World!"
        finally:
            await module.stop()


class TestWorkerProperties:
    """Tests for TaskWorker properties."""

    @pytest.mark.asyncio
    async def test_worker_has_unique_id(self, worker_env):
        """Test that worker has a unique identifier."""
        module, queue, session_factory, container = worker_env

        worker1 = TaskWorker(
            container=container,
            settings=module._settings,
            queue=queue,
            session_factory=session_factory,
        )

        worker2 = TaskWorker(
            container=container,
            settings=module._settings,
            queue=queue,
            session_factory=session_factory,
        )

        assert worker1.worker_id != worker2.worker_id

    @pytest.mark.asyncio
    async def test_worker_custom_id(self, worker_env):
        """Test that worker accepts custom ID."""
        module, queue, session_factory, container = worker_env

        worker = TaskWorker(
            container=container,
            settings=module._settings,
            queue=queue,
            session_factory=session_factory,
            worker_id="my-custom-worker",
        )

        assert worker.worker_id == "my-custom-worker"

    @pytest.mark.asyncio
    async def test_worker_is_running_property(self, worker_env):
        """Test that is_running reflects worker state."""
        module, queue, session_factory, container = worker_env

        worker = TaskWorker(
            container=container,
            settings=module._settings,
            queue=queue,
            session_factory=session_factory,
        )

        # Not running initially
        assert worker.is_running is False


class TestWorkerTimeout:
    """Tests for task execution timeout."""

    @pytest.mark.asyncio
    async def test_task_timeout_schedules_retry(self, test_db):
        """Test that tasks exceeding timeout are scheduled for retry (with retries remaining)."""
        import asyncio

        from sqlalchemy.ext.asyncio import AsyncEngine

        data_module, session_factory = test_db

        # Create module with minimum timeout for testing (must be >= 1 second)
        settings = TasksSettings(
            poll_interval=0.1,
            task_timeout=1.0,  # 1 second timeout (minimum allowed)
        )
        module = TasksModule(settings=settings, auto_create_tables=True)

        container = Container()
        container.register(type(session_factory), lambda: session_factory, scope=SINGLETON)

        engine = session_factory._sessionmaker.kw.get("bind")
        if engine:
            container.register(AsyncEngine, lambda: engine, scope=SINGLETON)

        module.configure(container)
        container.compile()
        module.finalize(container)
        await module.start()

        try:

            @task(max_retries=2)
            async def slow_task_with_retries() -> str:
                await asyncio.sleep(5.0)  # Takes 5 seconds, but timeout is 1s
                return "completed"

            task_id = await slow_task_with_retries.send()

            queue = module.get_queue()
            worker = TaskWorker(
                container=container,
                settings=settings,
                queue=queue,
                session_factory=session_factory,
            )

            await worker.run_once()

            async with session_factory.session_context() as session:
                record = await queue.get_task(session, task_id)

            # Task should be PENDING (scheduled for retry)
            assert record.status == TaskStatus.PENDING.value
            assert record.retry_count == 1
            assert "timeout" in record.error_message.lower()
        finally:
            await module.stop()

    @pytest.mark.asyncio
    async def test_task_timeout_fails_when_no_retries(self, test_db):
        """Test that tasks exceeding timeout are FAILED when no retries remain."""
        import asyncio

        from sqlalchemy.ext.asyncio import AsyncEngine

        data_module, session_factory = test_db

        settings = TasksSettings(
            poll_interval=0.1,
            task_timeout=1.0,
        )
        module = TasksModule(settings=settings, auto_create_tables=True)

        container = Container()
        container.register(type(session_factory), lambda: session_factory, scope=SINGLETON)

        engine = session_factory._sessionmaker.kw.get("bind")
        if engine:
            container.register(AsyncEngine, lambda: engine, scope=SINGLETON)

        module.configure(container)
        container.compile()
        module.finalize(container)
        await module.start()

        try:

            @task(max_retries=0)  # No retries
            async def slow_task_no_retry() -> str:
                await asyncio.sleep(5.0)
                return "completed"

            task_id = await slow_task_no_retry.send()

            queue = module.get_queue()
            worker = TaskWorker(
                container=container,
                settings=settings,
                queue=queue,
                session_factory=session_factory,
            )

            await worker.run_once()

            async with session_factory.session_context() as session:
                record = await queue.get_task(session, task_id)

            # Task should be FAILED (no retries allowed)
            assert record.status == TaskStatus.FAILED.value
            assert "timeout" in record.error_message.lower()
        finally:
            await module.stop()


class TestConcurrentWorkers:
    """Tests for concurrent worker task claiming.

    Note: SQLite doesn't support FOR UPDATE SKIP LOCKED, so true concurrency
    testing requires PostgreSQL. These tests verify the sequential behavior
    and task distribution at least.
    """

    @pytest.mark.asyncio
    async def test_multiple_workers_process_different_tasks(self, worker_env):
        """Test that multiple workers can each process different tasks.

        With SQLite, workers may claim overlapping tasks since SKIP LOCKED
        isn't supported. This test verifies that at minimum, all tasks
        get processed when multiple workers cooperate.
        """

        module, queue, session_factory, container = worker_env

        @task
        async def simple_work(value: int) -> int:
            return value * 2

        # Create multiple tasks
        task_ids = []
        for i in range(4):
            task_id = await simple_work.send(value=i)
            task_ids.append(task_id)

        worker1 = TaskWorker(
            container=container,
            settings=module._settings,
            queue=queue,
            session_factory=session_factory,
            worker_id="worker-1",
        )

        worker2 = TaskWorker(
            container=container,
            settings=module._settings,
            queue=queue,
            session_factory=session_factory,
            worker_id="worker-2",
        )

        # Run workers sequentially to ensure deterministic behavior
        await worker1.run_once()
        await worker2.run_once()
        await worker1.run_once()
        await worker2.run_once()

        # Verify all tasks completed
        completed_count = 0
        for task_id in task_ids:
            async with session_factory.session_context() as session:
                record = await queue.get_task(session, task_id)
            if record.status == TaskStatus.COMPLETED.value:
                completed_count += 1

        assert completed_count == 4, f"Expected all 4 tasks completed, got {completed_count}"

    @pytest.mark.asyncio
    async def test_workers_claim_batch_of_tasks(self, worker_env):
        """Test that a worker can claim and process a batch of tasks."""
        module, queue, session_factory, container = worker_env

        @task
        async def batch_item(n: int) -> int:
            return n

        # Create tasks
        for i in range(5):
            await batch_item.send(n=i)

        worker = TaskWorker(
            container=container,
            settings=module._settings,
            queue=queue,
            session_factory=session_factory,
        )

        # Single run_once should claim up to claim_batch_size tasks
        processed = await worker.run_once()
        assert processed >= 1  # At least one task processed

        # Run again to process remaining
        while True:
            more = await worker.run_once()
            if more == 0:
                break

        # Verify all completed
        async with session_factory.session_context() as session:
            stats = await queue.get_stats(session)

        assert stats["completed"] == 5
        assert stats["pending"] == 0
