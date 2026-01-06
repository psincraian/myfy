"""Tests for CLI command registry."""

import pytest

from myfy.cli.command import Command
from myfy.cli.registry import CommandRegistry


@pytest.fixture
def registry():
    """Create a fresh registry for each test."""
    # Reset singleton
    CommandRegistry.reset()
    return CommandRegistry.get_instance()


class TestCommandRegistry:
    """Tests for CommandRegistry class."""

    def test_singleton_pattern(self, registry):
        """Test that get_instance returns the same instance."""
        instance1 = CommandRegistry.get_instance()
        instance2 = CommandRegistry.get_instance()
        assert instance1 is instance2

    def test_reset_clears_singleton(self):
        """Test that reset creates a new instance."""
        instance1 = CommandRegistry.get_instance()
        CommandRegistry.reset()
        instance2 = CommandRegistry.get_instance()
        assert instance1 is not instance2

    def test_register_command(self, registry):
        """Test registering a command."""

        def my_cmd() -> None:
            pass

        cmd = Command(handler=my_cmd, name="my-cmd")
        registry.register(cmd)

        assert len(registry) == 1
        assert registry.get("my-cmd") is cmd

    def test_register_grouped_command(self, registry):
        """Test registering a grouped command."""

        def create_user() -> None:
            pass

        cmd = Command(handler=create_user, name="create", group="users")
        registry.register(cmd)

        assert registry.get("users:create") is cmd
        assert "users" in registry.get_groups()
        assert cmd in registry.get_group("users")

    def test_get_commands(self, registry):
        """Test getting all commands."""

        def cmd1() -> None:
            pass

        def cmd2() -> None:
            pass

        registry.register(Command(handler=cmd1, name="cmd1"))
        registry.register(Command(handler=cmd2, name="cmd2"))

        commands = registry.get_commands()
        assert len(commands) == 2

    def test_get_nonexistent_command(self, registry):
        """Test getting a command that doesn't exist."""
        assert registry.get("nonexistent") is None

    def test_get_empty_group(self, registry):
        """Test getting commands from non-existent group."""
        assert registry.get_group("nonexistent") == []

    def test_len(self, registry):
        """Test __len__ method."""

        def cmd1() -> None:
            pass

        def cmd2() -> None:
            pass

        assert len(registry) == 0
        registry.register(Command(handler=cmd1, name="cmd1"))
        assert len(registry) == 1
        registry.register(Command(handler=cmd2, name="cmd2"))
        assert len(registry) == 2

    def test_repr(self, registry):
        """Test __repr__ method."""

        def cmd() -> None:
            pass

        registry.register(Command(handler=cmd, name="cmd", group="grp"))

        repr_str = repr(registry)
        assert "commands=1" in repr_str
        assert "groups=1" in repr_str
