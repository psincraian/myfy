"""
Extension protocols for CLI module.

Defines protocols that other modules can implement to provide commands.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .command import Command
    from .registry import CommandRegistry


@runtime_checkable
class ICommandProvider(Protocol):
    """
    Protocol for modules that provide CLI commands.

    Modules implementing this protocol will have their commands
    discovered and registered by the CliModule.

    Example:
        ```python
        class MyModule:
            @property
            def provides(self) -> list[type]:
                return [ICommandProvider]

            def get_commands(self) -> list[Command]:
                return [
                    Command(handler=my_func, name="my-command"),
                ]
        ```
    """

    def get_commands(self) -> list[Command]:
        """
        Get commands provided by this module.

        Returns:
            List of Command instances to register
        """
        ...


@runtime_checkable
class ICliExtension(Protocol):
    """
    Protocol for extending CLI functionality.

    Modules implementing this protocol can add middleware, hooks,
    or other extensions to CLI command execution.
    """

    def extend_cli(self, registry: CommandRegistry) -> None:
        """
        Extend CLI functionality.

        Called after all commands are registered, allowing modules
        to add wrappers, middleware, or modify commands.

        Args:
            registry: The command registry
        """
        ...
