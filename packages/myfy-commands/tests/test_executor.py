"""Tests for CommandExecutor."""

import pytest

from myfy.commands.command import Command, CommandOption
from myfy.commands.errors import CommandExecutionError
from myfy.commands.executor import CommandExecutor


class MockContainer:
    """Mock DI container for testing."""

    def __init__(self):
        self._services = {}

    def register(self, type_, instance):
        self._services[type_] = instance

    def get(self, type_):
        if type_ not in self._services:
            raise KeyError(f"Service not found: {type_}")
        return self._services[type_]


class UserService:
    """Mock service for testing."""

    def get_users(self):
        return ["user1", "user2"]


@pytest.fixture
def container():
    """Create a mock container with services."""
    container = MockContainer()
    container.register(UserService, UserService())
    return container


@pytest.fixture
def executor(container):
    """Create an executor with mock container."""
    return CommandExecutor(container)


def test_compile_command(executor):
    """Test compiling a command creates an execution plan."""
    async def my_command():
        pass

    command = Command(name="test", handler=my_command)
    executor.compile_command(command)

    assert executor.is_compiled("test")


def test_execute_simple_command(executor):
    """Test executing a simple command without dependencies."""
    result_holder = []

    async def my_command():
        result_holder.append("executed")
        return "done"

    command = Command(name="test", handler=my_command)
    executor.compile_command(command)

    result = executor.execute(command, {})

    assert result == "done"
    assert "executed" in result_holder


def test_execute_command_with_cli_args(executor):
    """Test executing command with CLI arguments."""
    async def my_command(count: int, name: str):
        return f"{name}: {count}"

    command = Command(
        name="test",
        handler=my_command,
        options=[
            CommandOption(name="count", type_hint=int, default=10),
            CommandOption(name="name", type_hint=str, default="default"),
        ],
    )
    executor.compile_command(command)

    result = executor.execute(command, {"count": 5, "name": "test"})

    assert result == "test: 5"


def test_execute_command_with_dependency_injection(executor, container):  # noqa: ARG001
    """Test executing command with DI dependencies."""
    async def my_command(user_service: UserService):
        return user_service.get_users()

    command = Command(
        name="test",
        handler=my_command,
        dependencies=["user_service"],
    )
    executor.compile_command(command)

    result = executor.execute(command, {})

    assert result == ["user1", "user2"]


def test_execute_command_with_mixed_params(executor, container):  # noqa: ARG001
    """Test executing command with both CLI args and DI."""
    async def my_command(user_service: UserService, limit: int):
        users = user_service.get_users()
        return users[:limit]

    command = Command(
        name="test",
        handler=my_command,
        dependencies=["user_service"],
        options=[CommandOption(name="limit", type_hint=int, default=10)],
    )
    executor.compile_command(command)

    result = executor.execute(command, {"limit": 1})

    assert result == ["user1"]


def test_execute_sync_command(executor):
    """Test executing a synchronous command."""
    def my_sync_command(name: str):
        return f"Hello, {name}"

    command = Command(
        name="test",
        handler=my_sync_command,
        options=[CommandOption(name="name", type_hint=str, default="World")],
    )
    executor.compile_command(command)

    result = executor.execute(command, {"name": "Test"})

    assert result == "Hello, Test"


def test_execute_uncompiled_command_raises(executor):
    """Test that executing uncompiled command raises."""
    async def my_command():
        pass

    command = Command(name="uncompiled", handler=my_command)

    with pytest.raises(RuntimeError) as exc_info:
        executor.execute(command, {})

    assert "not compiled" in str(exc_info.value)


def test_execute_command_with_missing_dependency_raises(executor):
    """Test that missing dependency raises error."""

    class MissingService:
        pass

    async def my_command(missing: MissingService):
        pass

    command = Command(
        name="test",
        handler=my_command,
        dependencies=["missing"],
    )
    executor.compile_command(command)

    with pytest.raises(CommandExecutionError):
        executor.execute(command, {})


def test_execute_command_that_raises(executor):
    """Test that command exceptions are wrapped."""
    async def failing_command():
        raise ValueError("Something went wrong")

    command = Command(name="test", handler=failing_command)
    executor.compile_command(command)

    with pytest.raises(CommandExecutionError) as exc_info:
        executor.execute(command, {})

    assert "Something went wrong" in str(exc_info.value.cause)  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_execute_async_method(executor):
    """Test the async execution method."""
    async def my_command():
        return "async result"

    command = Command(name="test", handler=my_command)
    executor.compile_command(command)

    result = await executor.execute_async(command, {})

    assert result == "async result"


@pytest.mark.asyncio
async def test_execute_async_with_dependencies(executor, container):  # noqa: ARG001
    """Test async execution with DI."""
    async def my_command(user_service: UserService):
        return len(user_service.get_users())

    command = Command(
        name="test",
        handler=my_command,
        dependencies=["user_service"],
    )
    executor.compile_command(command)

    result = await executor.execute_async(command, {})

    assert result == 2  # noqa: PLR2004
