"""Test fixtures for myfy-tasks."""

import pytest
import pytest_asyncio

from myfy.tasks.registry import TaskRegistry


@pytest.fixture(autouse=True)
def clear_task_registry():
    """Clear task registry before and after each test."""
    TaskRegistry.get_instance().clear()
    yield
    TaskRegistry.get_instance().clear()


@pytest_asyncio.fixture
async def test_db():
    """Create an in-memory SQLite database for testing."""
    from myfy.data.testing import test_database

    async with test_database(
        database_url="sqlite+aiosqlite:///:memory:",
        echo=False,
    ) as (data_module, session_factory):
        yield data_module, session_factory


@pytest_asyncio.fixture
async def task_runner(test_db):
    """
    Fixture providing TestTaskRunner for integration tests.

    Usage:
        async def test_my_task(task_runner):
            @task
            async def my_task(x: int) -> int:
                return x * 2

            task_id = await my_task.send(x=5)
            await task_runner.process_pending()

            assert task_runner.was_called(my_task)
            assert task_runner.last_call(my_task).result == 10
    """
    from myfy.tasks.testing import test_task_runner

    _, session_factory = test_db
    async with test_task_runner(session_factory) as runner:
        yield runner
