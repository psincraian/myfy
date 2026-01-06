"""Tests for CliModule."""

import pytest

from myfy.cli.decorator import command
from myfy.cli.module import CliModule
from myfy.cli.registry import CommandRegistry
from myfy.core.di import Container


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset the registry before each test."""
    CommandRegistry.reset()
    yield
    CommandRegistry.reset()


class TestCliModule:
    """Tests for CliModule class."""

    def test_module_name(self):
        """Test module name property."""
        module = CliModule()
        assert module.name == "cli"

    def test_module_requires(self):
        """Test module has no dependencies."""
        module = CliModule()
        assert module.requires == []

    def test_module_provides(self):
        """Test module provides ICommandProvider."""
        from myfy.cli.extensions import ICommandProvider

        module = CliModule()
        assert ICommandProvider in module.provides

    def test_configure_registers_registry(self):
        """Test that configure registers CommandRegistry in container."""
        module = CliModule()
        container = Container()

        module.configure(container)
        container.compile()

        registry = container.get(CommandRegistry)
        assert registry is not None
        assert isinstance(registry, CommandRegistry)

    def test_get_commands_after_configure(self):
        """Test getting commands after module is configured."""
        # Register a command first
        @command
        def test_cmd() -> None:
            pass

        module = CliModule()
        container = Container()
        module.configure(container)

        commands = module.get_commands()
        assert len(commands) == 1
        assert commands[0].name == "test-cmd"

    def test_get_registry(self):
        """Test getting the registry from module."""
        module = CliModule()
        container = Container()
        module.configure(container)

        registry = module.get_registry()
        assert isinstance(registry, CommandRegistry)

    def test_get_commands_before_configure_raises(self):
        """Test that get_commands raises if module not configured."""
        module = CliModule()

        with pytest.raises(RuntimeError, match="not configured"):
            module.get_commands()

    def test_repr(self):
        """Test module string representation."""
        module = CliModule()
        assert "CliModule" in repr(module)

        # After configure
        container = Container()
        module.configure(container)
        repr_str = repr(module)
        assert "commands=" in repr_str

    @pytest.mark.asyncio
    async def test_start_stop_are_noops(self):
        """Test that start and stop are no-ops."""
        module = CliModule()
        container = Container()
        module.configure(container)

        # Should not raise
        await module.start()
        await module.stop()
