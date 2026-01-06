"""Unit tests for @task decorator."""

from myfy.tasks import TaskContext, task
from myfy.tasks.registry import TaskRegistry


def test_task_decorator_registers_task():
    """Test that @task decorator registers task in registry."""

    @task
    async def my_task(x: int) -> int:
        return x * 2

    registry = TaskRegistry.get_instance()
    # Task name includes module path + function name
    assert my_task.name in registry


def test_task_decorator_with_custom_name():
    """Test @task with custom name."""

    @task(name="custom.task.name")
    async def another_task() -> None:
        pass

    registry = TaskRegistry.get_instance()
    assert "custom.task.name" in registry
    assert another_task.name == "custom.task.name"


def test_task_decorator_with_options():
    """Test @task with max_retries and retry_on."""

    @task(max_retries=5, retry_on=[ValueError, TypeError])
    async def retry_task(x: int) -> int:
        return x

    assert retry_task.max_retries == 5
    assert ValueError in retry_task.retry_on
    assert TypeError in retry_task.retry_on


def test_task_detects_task_context():
    """Test that task correctly identifies TaskContext parameter."""

    @task
    async def task_with_context(data: str, ctx: TaskContext) -> str:
        return data

    assert task_with_context.has_context is True

    @task
    async def task_without_context(data: str) -> str:
        return data

    assert task_without_context.has_context is False


def test_task_categorizes_parameters():
    """Test that task correctly categorizes parameters."""

    class MyService:
        pass

    @task
    async def complex_task(
        name: str,
        count: int,
        enabled: bool,
        ctx: TaskContext,
        service: MyService,
    ) -> None:
        pass

    # Primitives should be task args
    assert "name" in complex_task._task_args
    assert "count" in complex_task._task_args
    assert "enabled" in complex_task._task_args

    # Complex types should be injectable
    assert "service" in complex_task.injectable_params
    assert complex_task.injectable_params["service"] is MyService

    # TaskContext is handled separately
    assert "ctx" not in complex_task._task_args
    assert "ctx" not in complex_task.injectable_params
    assert complex_task.has_context is True


def test_task_is_callable():
    """Test that decorated task is still callable."""

    @task
    async def simple_task(x: int) -> int:
        return x * 2

    # Should be able to call directly (for testing)
    import asyncio

    result = asyncio.run(simple_task(5))
    assert result == 10


def test_task_preserves_function_metadata():
    """Test that decorator preserves function metadata."""

    @task
    async def documented_task(x: int) -> int:
        """This is the docstring."""
        return x

    assert documented_task.func.__doc__ == """This is the docstring."""
    assert documented_task.func.__name__ == "documented_task"
