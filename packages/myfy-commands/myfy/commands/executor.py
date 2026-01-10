"""
Command execution with dependency injection.

Compiles injection plans for commands at startup and executes
them with resolved dependencies.
"""

from __future__ import annotations

import asyncio
import logging
from inspect import iscoroutinefunction
from typing import TYPE_CHECKING, Any, get_type_hints

from .command import Command
from .errors import CommandExecutionError

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class CommandExecutor:
    """
    Executes CLI command handlers with dependency injection.

    Resolves dependencies from the DI container and injects them
    along with CLI arguments and options, similar to HandlerExecutor
    for web routes.

    Example:
        ```python
        executor = CommandExecutor(container)

        # Compile all commands at startup
        for command in registry.get_all().values():
            executor.compile_command(command)

        # Execute a command
        cli_args = {"count": 20}
        result = executor.execute(command, cli_args)
        ```
    """

    def __init__(self, container: Any) -> None:
        """
        Initialize the executor.

        Args:
            container: DI container for resolving dependencies
        """
        self.container = container
        self._execution_plans: dict[str, Callable[..., Any]] = {}
        self._logger = logging.getLogger(__name__)

    def compile_command(self, command: Command) -> None:
        """
        Compile an execution plan for a command.

        Analyzes the handler signature and builds a fast execution path
        that resolves dependencies and converts CLI arguments.

        Args:
            command: The command to compile
        """
        # Get type hints for dependency resolution
        try:
            hints = get_type_hints(command.handler)
        except Exception:
            hints = {}

        # Build execution plan
        def execute(cli_args: dict[str, Any]) -> Any:
            kwargs = dict(cli_args)

            # Inject dependencies from container
            for param_name in command.dependencies:
                param_type = hints.get(param_name)
                if param_type:
                    try:
                        kwargs[param_name] = self.container.get(param_type)
                    except Exception as e:
                        self._logger.exception(
                            "Dependency injection failed",
                            exc_info=e,
                            extra={"param_name": param_name, "param_type": str(param_type)},
                        )
                        raise CommandExecutionError(command.full_name, e) from e

            # Execute handler (sync or async)
            try:
                if iscoroutinefunction(command.handler):
                    # Get or create event loop
                    try:
                        loop = asyncio.get_running_loop()
                        # Already in async context - create task
                        future = asyncio.ensure_future(command.handler(**kwargs))
                        return loop.run_until_complete(future)
                    except RuntimeError:
                        # No running loop - use asyncio.run
                        return asyncio.run(command.handler(**kwargs))
                else:
                    return command.handler(**kwargs)
            except Exception as e:
                self._logger.exception(
                    f"Command execution failed: {command.full_name}",
                    exc_info=e,
                )
                raise CommandExecutionError(command.full_name, e) from e

        self._execution_plans[command.full_name] = execute

    async def execute_async(self, command: Command, cli_args: dict[str, Any]) -> Any:
        """
        Execute a command handler asynchronously.

        This is the preferred method when running in an async context.

        Args:
            command: The command to execute
            cli_args: CLI arguments and options

        Returns:
            The command's return value
        """
        plan = self._execution_plans.get(command.full_name)
        if plan is None:
            raise RuntimeError(f"Command not compiled: {command.full_name}")

        # Get type hints for dependency resolution
        try:
            hints = get_type_hints(command.handler)
        except Exception:
            hints = {}

        kwargs = dict(cli_args)

        # Inject dependencies from container
        for param_name in command.dependencies:
            param_type = hints.get(param_name)
            if param_type:
                try:
                    kwargs[param_name] = self.container.get(param_type)
                except Exception as e:
                    self._logger.exception(
                        "Dependency injection failed",
                        exc_info=e,
                        extra={"param_name": param_name, "param_type": str(param_type)},
                    )
                    raise CommandExecutionError(command.full_name, e) from e

        # Execute handler
        try:
            if iscoroutinefunction(command.handler):
                return await command.handler(**kwargs)
            else:
                return command.handler(**kwargs)
        except Exception as e:
            self._logger.exception(
                f"Command execution failed: {command.full_name}",
                exc_info=e,
            )
            raise CommandExecutionError(command.full_name, e) from e

    def execute(self, command: Command, cli_args: dict[str, Any]) -> Any:
        """
        Execute a command handler synchronously.

        Args:
            command: The command to execute
            cli_args: CLI arguments and options

        Returns:
            The command's return value
        """
        plan = self._execution_plans.get(command.full_name)
        if plan is None:
            raise RuntimeError(f"Command not compiled: {command.full_name}")
        return plan(cli_args)

    def is_compiled(self, command_name: str) -> bool:
        """Check if a command has been compiled."""
        return command_name in self._execution_plans
