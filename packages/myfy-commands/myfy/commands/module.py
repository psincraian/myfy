"""
CLI module for user-defined commands.

Provides the CliModule that enables @cli.command decorators
and integrates with the myfy CLI.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from myfy.core.config import load_settings
from myfy.core.di import SINGLETON
from myfy.core.di.types import ProviderKey

from .config import CliSettings
from .executor import CommandExecutor
from .registry import CommandRegistry

if TYPE_CHECKING:
    from myfy.core.di import Container

logger = logging.getLogger(__name__)


class CliModule:
    """
    CLI module - provides user-defined command capabilities.

    Features:
    - @cli.command decorator for defining commands
    - Full DI injection in command handlers
    - Integration with myfy CLI via `myfy app <command>`
    - Command groups for organization

    Lifecycle (per ADR-0005):
    - configure(): Register services in DI container
    - extend(): No-op
    - finalize(): Compile command execution plans
    - start(): No-op (commands run with full app lifecycle)
    - stop(): No-op

    Example:
        ```python
        from myfy.core import Application
        from myfy.commands import CliModule, cli

        @cli.command()
        async def seed_users(user_service: UserService, count: int = 10):
            '''Seed the database with test users.'''
            for i in range(count):
                await user_service.create(f"user{i}@example.com")

        app = Application()
        app.add_module(CliModule())

        # Run with: myfy app seed-users --count 20
        ```

    Configuration:
        Environment variables use the MYFY_CLI_ prefix:
        - MYFY_CLI_VERBOSE: Enable verbose output
        - MYFY_CLI_NO_COLOR: Disable colored output
        - MYFY_CLI_TIMEOUT: Command execution timeout
    """

    def __init__(
        self,
        settings: CliSettings | None = None,
    ) -> None:
        """
        Initialize CliModule.

        Args:
            settings: Optional pre-configured settings.
                     If not provided, settings are loaded from environment.
        """
        self._settings = settings
        self._executor: CommandExecutor | None = None
        self._container: Container | None = None

    @property
    def name(self) -> str:
        """Module name for identification."""
        return "cli"

    @property
    def requires(self) -> list[type]:
        """
        Module dependencies.

        CliModule has no required dependencies - it can be used standalone
        or in combination with any other modules.
        """
        return []

    @property
    def provides(self) -> list[type]:
        """Extension protocols provided by this module."""
        return []

    def configure(self, container: Container) -> None:
        """
        Register CLI services in DI container.

        Registers:
        - CliSettings: Configuration for CLI module
        - CommandRegistry: Registry of all defined commands

        Args:
            container: DI container to register services in
        """
        logger.debug("Configuring CliModule...")

        self._container = container

        # Check if CliSettings already registered (nested settings pattern)
        key = ProviderKey(CliSettings)
        if key not in container._providers:
            if self._settings is None:
                self._settings = load_settings(CliSettings)
            container.register(
                type_=CliSettings,
                factory=lambda: self._settings,
                scope=SINGLETON,
            )

        # Register registry as singleton
        container.register(
            type_=CommandRegistry,
            factory=CommandRegistry.get_instance,
            scope=SINGLETON,
        )

        logger.debug("CliModule configured")

    def extend(self, container: Container) -> None:
        """
        Extend other modules (no-op for CliModule).

        CliModule doesn't extend other modules' service registrations.
        """
        pass

    def finalize(self, container: Container) -> None:
        """
        Finalize module configuration after container compilation.

        Compiles execution plans for all registered commands,
        building fast injection paths for each command handler.

        Args:
            container: Compiled DI container
        """
        self._executor = CommandExecutor(container)

        # Compile all registered commands
        registry = CommandRegistry.get_instance()
        for command in registry.get_all().values():
            self._executor.compile_command(command)

        command_count = len(registry)
        if command_count > 0:
            logger.info(f"CliModule finalized with {command_count} command(s)")
        else:
            logger.debug("CliModule finalized (no commands registered)")

    async def start(self) -> None:
        """
        Start CLI module.

        No-op for CliModule. Commands are executed on-demand via
        `myfy app <command>` with full application lifecycle.
        """
        pass

    async def stop(self) -> None:
        """
        Stop CLI module.

        No-op for CliModule. Cleanup happens at application shutdown.
        """
        pass

    def get_executor(self) -> CommandExecutor:
        """
        Get the command executor.

        Returns:
            The compiled CommandExecutor

        Raises:
            RuntimeError: If module not finalized yet
        """
        if self._executor is None:
            raise RuntimeError("CliModule not finalized - call Application.initialize() first")
        return self._executor

    def get_registry(self) -> CommandRegistry:
        """
        Get the command registry.

        Returns:
            The global CommandRegistry singleton
        """
        return CommandRegistry.get_instance()

    def get_settings(self) -> CliSettings:
        """
        Get CLI settings.

        Returns:
            The CliSettings configuration

        Raises:
            RuntimeError: If module not configured yet
        """
        if self._settings is None:
            raise RuntimeError("CliModule not configured - call Application.initialize() first")
        return self._settings

    def __repr__(self) -> str:
        count = len(CommandRegistry.get_instance())
        return f"CliModule(commands={count})"


# Module instance for entry point auto-discovery
cli_module = CliModule()
