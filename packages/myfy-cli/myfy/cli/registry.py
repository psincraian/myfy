"""
Command registry for CLI commands.

Provides a central registry for all commands registered via @command decorator.
"""

from __future__ import annotations

import logging
from typing import ClassVar

from .command import Command

logger = logging.getLogger(__name__)


class CommandRegistry:
    """
    Global registry for CLI commands.

    Commands are registered via the @command decorator and collected
    during module finalization.

    Example:
        ```python
        @command
        def my_command(name: str) -> None:
            print(f"Hello, {name}!")

        # Access registry
        registry = CommandRegistry.get_instance()
        commands = registry.get_commands()
        ```
    """

    _instance: ClassVar[CommandRegistry | None] = None

    def __init__(self) -> None:
        """Initialize empty command registry."""
        self._commands: dict[str, Command] = {}
        self._groups: dict[str, list[Command]] = {}

    @classmethod
    def get_instance(cls) -> CommandRegistry:
        """
        Get the singleton registry instance.

        Returns:
            The global CommandRegistry instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """
        Reset the singleton instance.

        Primarily used for testing.
        """
        cls._instance = None

    def register(self, command: Command) -> None:
        """
        Register a command.

        Args:
            command: The Command to register

        Raises:
            ValueError: If a command with the same name already exists
        """
        full_name = command.full_name

        if full_name in self._commands:
            logger.warning(f"Command '{full_name}' is being re-registered")

        self._commands[full_name] = command

        # Track by group
        if command.group:
            if command.group not in self._groups:
                self._groups[command.group] = []
            self._groups[command.group].append(command)

        logger.debug(f"Registered command: {command}")

    def get(self, name: str) -> Command | None:
        """
        Get a command by name.

        Args:
            name: Command name (or group:name for grouped commands)

        Returns:
            The Command or None if not found
        """
        return self._commands.get(name)

    def get_commands(self) -> list[Command]:
        """
        Get all registered commands.

        Returns:
            List of all registered commands
        """
        return list(self._commands.values())

    def get_group(self, group_name: str) -> list[Command]:
        """
        Get all commands in a group.

        Args:
            group_name: The group name

        Returns:
            List of commands in the group
        """
        return self._groups.get(group_name, [])

    def get_groups(self) -> list[str]:
        """
        Get all group names.

        Returns:
            List of group names
        """
        return list(self._groups.keys())

    def __len__(self) -> int:
        """Return number of registered commands."""
        return len(self._commands)

    def __repr__(self) -> str:
        return f"CommandRegistry(commands={len(self._commands)}, groups={len(self._groups)})"
