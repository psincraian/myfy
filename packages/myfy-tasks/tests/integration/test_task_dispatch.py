"""Integration tests for task dispatch and execution flow."""

import pytest

from myfy.tasks import TaskContext, TaskStatus, task
from myfy.tasks.errors import TaskSerializationError


class TestFullTaskLifecycle:
    """Tests for complete task lifecycle: dispatch -> execute -> result."""

    @pytest.mark.asyncio
    async def test_simple_task_dispatch_and_execution(self, task_runner):
        """Test the full flow: define task -> send -> process -> verify."""

        @task
        async def add_numbers(a: int, b: int) -> int:
            return a + b

        # Dispatch task
        task_id = await add_numbers.send(a=2, b=3)
        assert task_id is not None

        # Execute via test runner
        processed = await task_runner.process_pending()
        assert processed == 1

        # Verify execution
        assert task_runner.was_called(add_numbers)
        call = task_runner.last_call(add_numbers)
        assert call.args == {"a": 2, "b": 3}
        assert call.result == 5
        assert call.error is None

    @pytest.mark.asyncio
    async def test_task_with_return_value_via_get_result(self, task_runner):
        """Test that get_result() retrieves the task result."""

        @task
        async def compute(x: int) -> int:
            return x * x

        task_id = await compute.send(x=7)
        await task_runner.process_pending()

        # Get result via API
        result = await compute.get_result(task_id, timeout=5.0)
        assert result.is_completed
        assert result.value == 49
        assert result.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_task_with_string_return(self, task_runner):
        """Test task with string return value."""

        @task
        async def greet(name: str) -> str:
            return f"Hello, {name}!"

        task_id = await greet.send(name="World")
        await task_runner.process_pending()

        result = await greet.get_result(task_id)
        assert result.value == "Hello, World!"

    @pytest.mark.asyncio
    async def test_task_with_dict_return(self, task_runner):
        """Test task with dict return value."""

        @task
        async def process_data(data: dict[str, int]) -> dict[str, int]:
            return {k: v * 2 for k, v in data.items()}

        task_id = await process_data.send(data={"a": 1, "b": 2})
        await task_runner.process_pending()

        result = await process_data.get_result(task_id)
        assert result.value == {"a": 2, "b": 4}

    @pytest.mark.asyncio
    async def test_task_with_no_return(self, task_runner):
        """Test task that returns None."""
        side_effect = []

        @task
        async def side_effect_task(value: str) -> None:
            side_effect.append(value)

        task_id = await side_effect_task.send(value="executed")
        await task_runner.process_pending()

        assert "executed" in side_effect
        result = await side_effect_task.get_result(task_id)
        assert result.is_completed
        assert result.value is None


class TestTaskDispatchOptions:
    """Tests for task dispatch options (_priority, _delay, _max_retries)."""

    @pytest.mark.asyncio
    async def test_task_with_priority(self, task_runner):
        """Test that _priority affects execution order."""
        execution_order = []

        @task
        async def ordered_task(name: str) -> str:
            execution_order.append(name)
            return name

        # Dispatch tasks in wrong order, but with priorities
        await ordered_task.send(name="low", _priority=1)  # type: ignore[call-arg]
        await ordered_task.send(name="high", _priority=10)  # type: ignore[call-arg]
        await ordered_task.send(name="medium", _priority=5)  # type: ignore[call-arg]

        # Process all
        await task_runner.process_pending()

        # High priority should execute first
        assert execution_order[0] == "high"
        assert execution_order[1] == "medium"
        assert execution_order[2] == "low"

    @pytest.mark.asyncio
    async def test_task_with_max_retries_override(self, task_runner):
        """Test that _max_retries overrides task default."""

        @task(max_retries=1)
        async def failing_task(attempt: int) -> None:
            raise ValueError("Always fails")

        # Override with more retries
        task_id = await failing_task.send(attempt=1, _max_retries=3)

        # Get the task record to verify
        async with task_runner.session_factory.session_context() as session:
            record = await task_runner.queue.get_task(session, task_id)

        assert record.max_retries == 3


class TestTaskContext:
    """Tests for TaskContext functionality."""

    @pytest.mark.asyncio
    async def test_task_with_context_progress(self, task_runner):
        """Test TaskContext.update_progress() stores progress."""

        @task
        async def progress_task(items: list[str], ctx: TaskContext) -> int:
            for i, _ in enumerate(items):
                await ctx.update_progress(current=i + 1, total=len(items))
            return len(items)

        task_id = await progress_task.send(items=["a", "b", "c"])  # type: ignore[call-arg]
        await task_runner.process_pending()

        # Check result includes progress info
        result = await progress_task.get_result(task_id)
        assert result.is_completed
        assert result.value == 3
        # Final progress should be 3/3
        assert result.progress == (3, 3)

    @pytest.mark.asyncio
    async def test_task_context_provides_task_id(self, task_runner):
        """Test that TaskContext provides correct task_id."""
        captured_id = []

        @task
        async def capture_id_task(ctx: TaskContext) -> str:
            captured_id.append(ctx.task_id)
            return ctx.task_id

        task_id = await capture_id_task.send()  # type: ignore[call-arg]
        await task_runner.process_pending()

        assert len(captured_id) == 1
        assert captured_id[0] == task_id

    @pytest.mark.asyncio
    async def test_task_context_provides_attempt_number(self, task_runner):
        """Test that TaskContext provides correct attempt number on first run."""
        captured_attempt = []

        @task
        async def capture_attempt(ctx: TaskContext) -> int:
            captured_attempt.append(ctx.attempt)
            return ctx.attempt

        await capture_attempt.send()  # type: ignore[call-arg]
        await task_runner.process_pending()

        # First attempt should be 1
        assert captured_attempt == [1]
        assert task_runner.last_call(capture_attempt).result == 1


class TestTaskFailureAndRetry:
    """Tests for task failure and retry behavior."""

    @pytest.mark.asyncio
    async def test_task_failure_records_error(self, task_runner):
        """Test that task failure is recorded correctly."""

        @task(max_retries=0)
        async def failing_task() -> None:
            raise ValueError("Expected failure")

        task_id = await failing_task.send()
        await task_runner.process_pending()

        result = await failing_task.get_result(task_id)
        assert result.is_failed
        assert result.status == TaskStatus.FAILED
        assert "Expected failure" in result.error  # type: ignore[operator]

    @pytest.mark.asyncio
    async def test_task_failure_schedules_retry(self, task_runner):
        """Test that failed task with retries is scheduled for retry."""

        @task(max_retries=2)
        async def fail_once() -> str:
            raise ValueError("Failed")

        task_id = await fail_once.send()
        await task_runner.process_pending()

        # Task should be pending (scheduled for retry) not failed
        result = await fail_once.get_result(task_id, timeout=0.1)
        assert result.status == TaskStatus.PENDING
        assert result.error is not None  # Error is recorded
        assert result.attempt == 2  # Will be attempt 2 on next run

    @pytest.mark.asyncio
    async def test_task_records_error_on_call(self, task_runner):
        """Test that TestTaskRunner records task errors."""

        @task(max_retries=0)
        async def error_task() -> None:
            raise RuntimeError("Test error")

        await error_task.send()
        await task_runner.process_pending()

        # Verify error was recorded
        call = task_runner.last_call(error_task)
        assert call is not None
        assert call.error is not None
        assert isinstance(call.error, RuntimeError)


class TestMultipleTasks:
    """Tests for multiple task execution."""

    @pytest.mark.asyncio
    async def test_multiple_tasks_all_execute(self, task_runner):
        """Test that multiple tasks all get executed."""

        @task
        async def simple_task(value: int) -> int:
            return value * 2

        # Dispatch multiple tasks
        ids = []
        for i in range(5):
            task_id = await simple_task.send(value=i)
            ids.append(task_id)

        # Process all
        processed = await task_runner.process_pending()
        assert processed == 5

        # Verify all completed
        for i, task_id in enumerate(ids):
            result = await simple_task.get_result(task_id)
            assert result.is_completed
            assert result.value == i * 2

    @pytest.mark.asyncio
    async def test_call_count_tracking(self, task_runner):
        """Test that TestTaskRunner tracks call counts."""

        @task
        async def counted_task(n: int) -> int:
            return n

        for i in range(3):
            await counted_task.send(n=i)

        await task_runner.process_pending()

        assert task_runner.call_count(counted_task) == 3


class TestTaskSerialization:
    """Tests for task argument serialization."""

    @pytest.mark.asyncio
    async def test_task_with_list_args(self, task_runner):
        """Test task with list arguments."""

        @task
        async def sum_list(numbers: list[int]) -> int:
            return sum(numbers)

        task_id = await sum_list.send(numbers=[1, 2, 3, 4, 5])
        await task_runner.process_pending()

        result = await sum_list.get_result(task_id)
        assert result.value == 15

    @pytest.mark.asyncio
    async def test_task_with_typed_dict(self, task_runner):
        """Test task with typed dict arguments."""

        @task
        async def process_config(config: dict[str, str]) -> str:
            return config.get("key", "default")

        task_id = await process_config.send(config={"key": "value"})
        await task_runner.process_pending()

        result = await process_config.get_result(task_id)
        assert result.value == "value"

    @pytest.mark.asyncio
    async def test_task_serialization_error(self, task_runner):
        """Test that non-serializable args raise TaskSerializationError."""

        @task
        async def bad_task(data: dict[str, object]) -> None:
            pass

        class NotSerializable:
            pass

        with pytest.raises(TaskSerializationError):
            await bad_task.send(data={"obj": NotSerializable()})
