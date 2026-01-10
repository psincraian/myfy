"""
Command registry for storing command definitions.

Provides a singleton registry for all registered commands,
following the same pattern as TaskRegistry.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .errors import CommandAlreadyRegisteredError, CommandNotFoundError

if TYPE_CHECKING:
    from .command import Command

logger = logging.getLogger(__name__)


class CommandRegistry:
    """
    Global registry of CLI command definitions.

    The registry is a singleton that stores all commands decorated with @cli.command.
    The CLI module uses this registry to look up command implementations by name.

    Example:
        ```python
        registry = CommandRegistry.get_instance()

        # Get a command by name
        command = registry.get("seed-users")

        # List all commands
        for name, cmd in registry.get_all().items():
            print(f"{name}: {cmd.help}")

        # Get commands by group
        groups = registry.get_groups()
        for group_name, commands in groups.items():
            print(f"Group: {group_name}")
        ```
    """

    _instance: CommandRegistry | None = None

    def __init__(self) -> None:
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
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance (for testing).

        Warning: This clears all registered commands.
        """
        cls._instance = None

    def register(self, command: Command) -> None:
        """
        Register a command definition.

        Args:
            command: The command to register

        Raises:
            CommandAlreadyRegisteredError: If a command with this name already exists
        """
        if command.full_name in self._commands:
            raise CommandAlreadyRegisteredError(command.full_name)

        self._commands[command.full_name] = command

        # Track by group
        group = command.group or "__default__"
        if group not in self._groups:
            self._groups[group] = []
        self._groups[group].append(command)

        logger.debug(f"Registered command: {command.full_name}")

    def get(self, name: str) -> Command:
        """
        Get a command definition by name.

        Args:
            name: The command name (e.g., "seed-users" or "db:seed")

        Returns:
            The command definition

        Raises:
            CommandNotFoundError: If the command is not registered
        """
        command = self._commands.get(name)
        if command is None:
            raise CommandNotFoundError(name)
        return command

    def get_or_none(self, name: str) -> Command | None:
        """
        Get a command definition by name, or None if not found.

        Args:
            name: The command name

        Returns:
            The command definition, or None if not registered
        """
        return self._commands.get(name)

    def get_all(self) -> dict[str, Command]:
        """
        Get all registered commands.

        Returns:
            Dictionary mapping command names to command definitions
        """
        return self._commands.copy()

    def get_groups(self) -> dict[str, list[Command]]:
        """
        Get commands organized by group.

        Returns:
            Dictionary mapping group names to lists of commands.
            Commands without a group are under "__default__".
        """
        return {k: list(v) for k, v in self._groups.items()}

    def clear(self) -> None:
        """
        Clear all registered commands (for testing).

        Warning: This removes all commands from the registry.
        """
        self._commands.clear()
        self._groups.clear()
        logger.debug("Cleared command registry")

    def __len__(self) -> int:
        """Return the number of registered commands."""
        return len(self._commands)

    def __contains__(self, name: str) -> bool:
        """Check if a command is registered."""
        return name in self._commands
