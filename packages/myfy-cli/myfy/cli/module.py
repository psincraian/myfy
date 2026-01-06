"""
CLI module for myfy.

Provides command-line command support for applications.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from myfy.core.di import SINGLETON

from .extensions import ICliExtension, ICommandProvider
from .registry import CommandRegistry

if TYPE_CHECKING:
    from myfy.core.di import Container

logger = logging.getLogger(__name__)


class CliModule:
    """
    CLI module - provides command-line command support.

    Features:
    - @command decorator for defining commands
    - DI integration for injecting services into commands
    - Command groups for organization
    - Async command support
    - Integration with `myfy app` CLI

    Lifecycle (per ADR-0005):
    - configure(): Register CommandRegistry in DI container
    - extend(): No-op
    - finalize(): Collect commands from all ICommandProvider modules
    - start(): No-op (CLI is invoked separately from app runtime)
    - stop(): No-op

    Example:
        ```python
        from myfy.core import Application
        from myfy.cli import CliModule, command

        @command
        async def seed_db(db: Database, count: int = 100) -> None:
            \"\"\"Seed the database with test data.\"\"\"
            for i in range(count):
                await db.create_record(...)
            print(f"Created {count} records")

        app = Application()
        app.add_module(CliModule())
        ```

    Usage:
        ```bash
        myfy app seed-db --count 200
        ```
    """

    def __init__(self) -> None:
        """Create CLI module."""
        self._registry: CommandRegistry | None = None

    @property
    def name(self) -> str:
        """Module name for registration."""
        return "cli"

    @property
    def requires(self) -> list[type]:
        """
        Module types this module depends on.

        CliModule has no hard dependencies.
        """
        return []

    @property
    def provides(self) -> list[type]:
        """
        Extension protocols provided by this module.

        Implements ICommandProvider for command access.
        """
        return [ICommandProvider]

    def configure(self, container: Container) -> None:
        """
        Configure CLI module.

        Registers CommandRegistry in the DI container.

        Args:
            container: The DI container
        """
        logger.debug("Configuring CliModule...")

        # Get or create the global registry
        self._registry = CommandRegistry.get_instance()

        # Register registry as singleton
        container.register(
            type_=CommandRegistry,
            factory=CommandRegistry.get_instance,
            scope=SINGLETON,
        )

        logger.debug("CliModule configured successfully")

    def extend(self, container: Container) -> None:
        """
        Extend other modules' services (no-op for CLI).

        CliModule doesn't need to extend other modules' services.
        This method exists for ADR-0005 lifecycle compliance.
        """

    def finalize(self, container: Container) -> None:
        """
        Finalize module configuration after container compilation.

        Collects commands from all modules implementing ICommandProvider.
        Also allows ICliExtension modules to extend CLI functionality.

        Args:
            container: The DI container (compiled, singletons accessible)
        """
        # Commands registered via @command decorator are already in the registry
        # Here we collect any additional commands from ICommandProvider modules

        # Note: To collect from other modules, we'd need access to the Application
        # For now, we rely on the @command decorator for registration

        logger.debug(f"CliModule finalized with {len(self._registry or [])} commands")

    async def start(self) -> None:
        """
        Start CLI module (no-op).

        CLI commands are executed separately from the application runtime.
        """

    async def stop(self) -> None:
        """
        Stop CLI module (no-op).

        No cleanup needed for CLI.
        """

    def get_commands(self):
        """
        Get all registered commands.

        Returns:
            List of Command instances

        Raises:
            RuntimeError: If module not configured
        """
        if self._registry is None:
            raise RuntimeError("CliModule not configured - call configure() first")
        return self._registry.get_commands()

    def get_registry(self) -> CommandRegistry:
        """
        Get the command registry.

        Returns:
            The CommandRegistry instance

        Raises:
            RuntimeError: If module not configured
        """
        if self._registry is None:
            raise RuntimeError("CliModule not configured - call configure() first")
        return self._registry

    def __repr__(self) -> str:
        """String representation of module."""
        cmd_count = len(self._registry) if self._registry else 0
        return f"CliModule(commands={cmd_count})"


# Module instance for entry point (optional auto-discovery)
cli_module = CliModule()
