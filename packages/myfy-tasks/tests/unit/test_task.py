"""Unit tests for Task class."""

import asyncio

from myfy.tasks import TaskContext, task
from myfy.tasks.task import _is_serializable_type


class TestSerializableType:
    """Tests for _is_serializable_type helper."""

    def test_primitive_types_are_serializable(self):
        """Primitive types should be serializable."""
        assert _is_serializable_type(str) is True
        assert _is_serializable_type(int) is True
        assert _is_serializable_type(float) is True
        assert _is_serializable_type(bool) is True
        assert _is_serializable_type(bytes) is True
        assert _is_serializable_type(type(None)) is True

    def test_generic_collections_are_serializable(self):
        """Generic collection types should be serializable."""
        assert _is_serializable_type(list[str]) is True
        assert _is_serializable_type(dict[str, int]) is True
        assert _is_serializable_type(set[int]) is True
        assert _is_serializable_type(tuple[str, int]) is True

    def test_complex_types_are_not_serializable(self):
        """Complex types should not be serializable (they get injected)."""

        class MyService:
            pass

        assert _is_serializable_type(MyService) is False
        assert _is_serializable_type(TaskContext) is False


class TestTaskParameterAnalysis:
    """Tests for Task parameter analysis."""

    def test_task_separates_args_from_injectables(self):
        """Task should correctly separate serializable args from injectable deps."""

        class EmailService:
            pass

        @task
        async def send_notification(
            user_id: str,
            message: str,
            priority: int,
            email_service: EmailService,
        ) -> None:
            pass

        # Primitive types are task args
        assert "user_id" in send_notification._task_args
        assert "message" in send_notification._task_args
        assert "priority" in send_notification._task_args

        # Complex types are injectable
        assert "email_service" in send_notification.injectable_params
        assert send_notification.injectable_params["email_service"] is EmailService

    def test_task_handles_list_and_dict_args(self):
        """Task should treat list and dict as serializable args."""

        @task
        async def batch_process(items: list[str], config: dict[str, int]) -> int:
            return len(items)

        assert "items" in batch_process._task_args
        assert "config" in batch_process._task_args
        assert len(batch_process.injectable_params) == 0

    def test_task_handles_no_type_hints(self):
        """Parameters without type hints should be treated as task args."""

        @task
        async def legacy_task(x, y, z):
            return x + y + z

        assert "x" in legacy_task._task_args
        assert "y" in legacy_task._task_args
        assert "z" in legacy_task._task_args


class TestTaskDirectExecution:
    """Tests for Task direct execution (bypassing queue)."""

    def test_task_is_directly_callable(self):
        """Task should be directly callable for testing."""

        @task
        async def multiply(a: int, b: int) -> int:
            return a * b

        result = asyncio.run(multiply(3, 4))  # type: ignore[arg-type]
        assert result == 12

    def test_task_direct_call_with_context(self):
        """Direct call should work even with TaskContext parameter."""

        @task
        async def process_with_ctx(value: int, ctx: TaskContext) -> int:
            # ctx won't be available in direct call - need to handle gracefully
            return value * 2

        # Verify task knows it has context (direct call not tested here
        # because ctx must be injected by worker)
        assert process_with_ctx.has_context is True


class TestTaskProperties:
    """Tests for Task property accessors."""

    def test_task_name_default(self):
        """Task name should default to module.qualname."""

        @task
        async def my_task() -> None:
            pass

        assert "my_task" in my_task.name
        assert "test_task" in my_task.name  # module name

    def test_task_name_custom(self):
        """Task should accept custom name."""

        @task(name="custom.task.identifier")
        async def another_task() -> None:
            pass

        assert another_task.name == "custom.task.identifier"

    def test_task_max_retries(self):
        """Task should store max_retries setting."""

        @task(max_retries=5)
        async def retry_task() -> None:
            pass

        assert retry_task.max_retries == 5

    def test_task_retry_on(self):
        """Task should store retry_on exception types."""

        @task(retry_on=[ValueError, ConnectionError])
        async def selective_retry_task() -> None:
            pass

        assert ValueError in selective_retry_task.retry_on
        assert ConnectionError in selective_retry_task.retry_on
        assert TypeError not in selective_retry_task.retry_on

    def test_task_is_async(self):
        """Task should detect async functions."""

        @task
        async def async_task() -> None:
            pass

        assert async_task.is_async is True

    def test_task_repr(self):
        """Task should have useful repr."""

        @task(name="repr.test")
        async def repr_task() -> None:
            pass

        assert "repr.test" in repr(repr_task)
        assert "Task" in repr(repr_task)
