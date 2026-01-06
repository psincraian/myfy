"""Tests for CLI command decorators."""

import pytest

from myfy.cli.decorator import command, group
from myfy.cli.registry import CommandRegistry


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset the registry before each test."""
    CommandRegistry.reset()
    yield
    CommandRegistry.reset()


class TestCommandDecorator:
    """Tests for @command decorator."""

    def test_simple_command(self):
        """Test decorating a simple function."""

        @command
        def greet(name: str) -> None:
            """Greet a user."""
            print(f"Hello, {name}!")

        # Function should be unchanged
        assert callable(greet)
        assert greet.__name__ == "greet"

        # Command should be registered
        registry = CommandRegistry.get_instance()
        cmd = registry.get("greet")
        assert cmd is not None
        assert cmd.name == "greet"
        assert cmd.help_text == "Greet a user."

    def test_command_with_name(self):
        """Test command with custom name."""

        @command(name="hello")
        def greet(name: str) -> None:
            pass

        registry = CommandRegistry.get_instance()
        cmd = registry.get("hello")
        assert cmd is not None
        assert cmd.name == "hello"

    def test_command_with_help(self):
        """Test command with custom help text."""

        @command(help="Custom help text")
        def my_cmd() -> None:
            """Docstring help."""
            pass

        registry = CommandRegistry.get_instance()
        cmd = registry.get("my-cmd")
        assert cmd.help_text == "Custom help text"

    def test_command_with_group(self):
        """Test command with group."""

        @command(group="users")
        def create(email: str) -> None:
            pass

        registry = CommandRegistry.get_instance()
        cmd = registry.get("users:create")
        assert cmd is not None
        assert cmd.group == "users"

    def test_command_name_from_function(self):
        """Test that underscores are converted to dashes."""

        @command
        def seed_database(count: int = 100) -> None:
            pass

        registry = CommandRegistry.get_instance()
        cmd = registry.get("seed-database")
        assert cmd is not None

    def test_async_command(self):
        """Test decorating an async function."""

        @command
        async def async_cmd(name: str) -> None:
            pass

        registry = CommandRegistry.get_instance()
        cmd = registry.get("async-cmd")
        assert cmd is not None
        assert cmd.is_async is True

    def test_multiple_commands(self):
        """Test registering multiple commands."""

        @command
        def cmd1() -> None:
            pass

        @command
        def cmd2() -> None:
            pass

        registry = CommandRegistry.get_instance()
        assert len(registry) == 2
        assert registry.get("cmd1") is not None
        assert registry.get("cmd2") is not None


class TestGroupDecorator:
    """Tests for @group decorator."""

    def test_group_decorator(self):
        """Test creating a command group from a class."""

        @group(name="users", help="User commands")
        class UserCommands:
            def create(email: str) -> None:
                """Create a user."""
                pass

            def delete(email: str) -> None:
                """Delete a user."""
                pass

        registry = CommandRegistry.get_instance()
        groups = registry.get_groups()
        assert "users" in groups

        user_cmds = registry.get_group("users")
        assert len(user_cmds) >= 2

    def test_group_command_names(self):
        """Test that group command names are converted properly."""

        @group(name="data")
        class DataCommands:
            def seed_db(count: int = 100) -> None:
                pass

        registry = CommandRegistry.get_instance()
        cmd = registry.get("data:seed-db")
        assert cmd is not None
