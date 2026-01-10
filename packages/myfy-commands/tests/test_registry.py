"""Tests for CommandRegistry."""

import pytest

from myfy.commands.command import Command
from myfy.commands.errors import CommandAlreadyRegisteredError, CommandNotFoundError
from myfy.commands.registry import CommandRegistry


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset registry before each test."""
    CommandRegistry.reset_instance()
    yield
    CommandRegistry.reset_instance()


def test_singleton_pattern():
    """Test that registry is a singleton."""
    instance1 = CommandRegistry.get_instance()
    instance2 = CommandRegistry.get_instance()
    assert instance1 is instance2


def test_reset_instance():
    """Test that reset creates a new instance."""
    instance1 = CommandRegistry.get_instance()
    CommandRegistry.reset_instance()
    instance2 = CommandRegistry.get_instance()
    assert instance1 is not instance2


def test_register_command():
    """Test registering a command."""
    registry = CommandRegistry.get_instance()

    async def my_handler():
        pass

    command = Command(name="test-cmd", handler=my_handler)
    registry.register(command)

    assert "test-cmd" in registry
    assert len(registry) == 1


def test_register_duplicate_raises():
    """Test that registering duplicate command raises."""
    registry = CommandRegistry.get_instance()

    async def handler1():
        pass

    async def handler2():
        pass

    command1 = Command(name="test-cmd", handler=handler1)
    command2 = Command(name="test-cmd", handler=handler2)

    registry.register(command1)

    with pytest.raises(CommandAlreadyRegisteredError) as exc_info:
        registry.register(command2)

    assert "test-cmd" in str(exc_info.value)


def test_get_command():
    """Test getting a command by name."""
    registry = CommandRegistry.get_instance()

    async def my_handler():
        pass

    command = Command(name="test-cmd", handler=my_handler)
    registry.register(command)

    retrieved = registry.get("test-cmd")
    assert retrieved is command


def test_get_nonexistent_raises():
    """Test that getting nonexistent command raises."""
    registry = CommandRegistry.get_instance()

    with pytest.raises(CommandNotFoundError) as exc_info:
        registry.get("nonexistent")

    assert "nonexistent" in str(exc_info.value)


def test_get_or_none():
    """Test get_or_none returns None for missing commands."""
    registry = CommandRegistry.get_instance()

    result = registry.get_or_none("nonexistent")
    assert result is None


def test_get_all():
    """Test getting all commands."""
    registry = CommandRegistry.get_instance()

    async def handler1():
        pass

    async def handler2():
        pass

    command1 = Command(name="cmd1", handler=handler1)
    command2 = Command(name="cmd2", handler=handler2)

    registry.register(command1)
    registry.register(command2)

    all_cmds = registry.get_all()
    assert len(all_cmds) == 2
    assert "cmd1" in all_cmds
    assert "cmd2" in all_cmds


def test_grouped_commands():
    """Test that commands are organized by group."""
    registry = CommandRegistry.get_instance()

    async def handler1():
        pass

    async def handler2():
        pass

    async def handler3():
        pass

    command1 = Command(name="seed", handler=handler1, group="db")
    command2 = Command(name="reset", handler=handler2, group="db")
    command3 = Command(name="users", handler=handler3)  # no group

    registry.register(command1)
    registry.register(command2)
    registry.register(command3)

    groups = registry.get_groups()

    assert "db" in groups
    assert len(groups["db"]) == 2
    assert "__default__" in groups
    assert len(groups["__default__"]) == 1


def test_clear_registry():
    """Test clearing the registry."""
    registry = CommandRegistry.get_instance()

    async def my_handler():
        pass

    command = Command(name="test-cmd", handler=my_handler)
    registry.register(command)

    assert len(registry) == 1

    registry.clear()

    assert len(registry) == 0
    assert "test-cmd" not in registry


def test_full_name_with_group():
    """Test full_name property with group."""
    async def handler():
        pass

    command = Command(name="seed", handler=handler, group="db")
    assert command.full_name == "db:seed"


def test_full_name_without_group():
    """Test full_name property without group."""
    async def handler():
        pass

    command = Command(name="seed", handler=handler)
    assert command.full_name == "seed"


def test_command_repr():
    """Test command string representation."""
    async def my_handler():
        pass

    command = Command(name="test", handler=my_handler, group="db")
    repr_str = repr(command)

    assert "db:test" in repr_str
    assert "my_handler" in repr_str
