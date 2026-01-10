"""
CLI command router and decorator factory.

Provides the @cli.command decorator API for defining commands,
similar to the Router for web routes.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, get_type_hints

import typer

from .command import Command, CommandArg, CommandOption
from .registry import CommandRegistry


class CliRouter:
    """
    CLI command registry and decorator factory.

    Provides decorator API for defining commands:
        ```python
        from myfy.commands import cli

        @cli.command()
        async def seed_users(user_service: UserService, count: int = 10):
            '''Seed the database with test users.'''
            ...

        # With command groups
        db = cli.group("db")

        @db.command()
        async def reset(db: Database, force: bool = False):
            '''Reset the database.'''
            ...
        ```

    Commands are registered at import time and executed via `myfy app <command>`.
    """

    def __init__(self) -> None:
        self._commands: list[Command] = []
        self._current_group: str | None = None

    def command(
        self,
        name: str | None = None,
        *,
        group: str | None = None,
        help: str | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator for CLI commands.

        Args:
            name: Command name (defaults to function name with underscores to hyphens)
            group: Group name for organization (e.g., "db" for "db:seed")
            help: Help text (defaults to docstring)

        Returns:
            Decorator that registers the command

        Example:
            ```python
            @cli.command()
            async def seed_users(count: int = 10):
                '''Seed users into the database.'''
                ...

            @cli.command(name="import-data", group="db")
            async def import_data(file: str):
                '''Import data from a file.'''
                ...
            ```
        """

        def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
            # Derive command name from function name if not provided
            cmd_name = name or handler.__name__.replace("_", "-")
            cmd_help = help or handler.__doc__
            cmd_group = group or self._current_group

            command = Command(
                name=cmd_name,
                handler=handler,
                group=cmd_group,
                help=cmd_help,
            )

            # Analyze handler signature for DI and CLI parameters
            self._analyze_handler(command)

            self._commands.append(command)
            CommandRegistry.get_instance().register(command)

            return handler

        return decorator

    def group(self, name: str) -> CliRouter:
        """
        Create a sub-router for grouped commands.

        Groups help organize related commands together.
        Grouped commands are accessed as `myfy app <group>:<command>`.

        Args:
            name: Group name (e.g., "db", "users")

        Returns:
            A new CliRouter scoped to this group

        Example:
            ```python
            db = cli.group("db")

            @db.command()
            async def seed(db: Database):
                '''Seed the database.'''
                ...

            @db.command()
            async def reset(db: Database, force: bool = False):
                '''Reset the database.'''
                ...

            # Commands available as:
            # myfy app db:seed
            # myfy app db:reset --force
            ```
        """
        sub_router = CliRouter()
        sub_router._current_group = name
        return sub_router

    def _analyze_handler(self, command: Command) -> None:
        """
        Analyze handler signature for DI dependencies and CLI parameters.

        Parameters are classified as (in order of precedence):
        1. Typer Argument -> positional CLI argument
        2. Typer Option -> CLI option/flag
        3. Primitive type with default -> CLI option
        4. Primitive type without default -> CLI argument
        5. Complex type -> DI dependency
        """
        sig = inspect.signature(command.handler)

        # Get type hints, handling potential errors
        try:
            hints = get_type_hints(command.handler)
        except Exception:
            hints = {}

        for param_name, param in sig.parameters.items():
            param_type = hints.get(param_name)
            default = param.default

            # Check if it's a Typer Argument
            if isinstance(default, typer.models.ArgumentInfo):
                command.arguments.append(
                    CommandArg(
                        name=param_name,
                        type_hint=param_type or str,
                        default=default.default if default.default is not ... else None,
                        help=default.help,
                        is_required=default.default is ...,
                    )
                )

            # Check if it's a Typer Option
            elif isinstance(default, typer.models.OptionInfo):
                # Extract short option if provided
                short = None
                if default.param_decls:
                    for decl in default.param_decls:
                        if decl.startswith("-") and not decl.startswith("--"):
                            short = decl
                            break

                command.options.append(
                    CommandOption(
                        name=param_name,
                        type_hint=param_type or str,
                        default=default.default if default.default is not ... else None,
                        help=default.help,
                        short=short,
                    )
                )

            # Primitive type -> CLI parameter
            elif self._is_primitive_type(param_type):
                if default is not inspect.Parameter.empty:
                    # Has default -> option
                    command.options.append(
                        CommandOption(
                            name=param_name,
                            type_hint=param_type or type(default),
                            default=default,
                        )
                    )
                else:
                    # No default -> required argument
                    command.arguments.append(
                        CommandArg(
                            name=param_name,
                            type_hint=param_type or str,
                            is_required=True,
                        )
                    )

            # Complex type -> DI dependency
            else:
                command.dependencies.append(param_name)

    def _is_primitive_type(self, type_hint: Any) -> bool:
        """Check if a type hint is a primitive CLI-compatible type."""
        if type_hint is None:
            return False

        # Handle Optional types
        origin = getattr(type_hint, "__origin__", None)
        if origin is not None:
            # For Optional[X], check if X is primitive
            args = getattr(type_hint, "__args__", ())
            if type(None) in args:
                # It's Optional[X], get the non-None type
                non_none_args = [a for a in args if a is not type(None)]
                if non_none_args:
                    return self._is_primitive_type(non_none_args[0])

        return type_hint in (int, float, str, bool)

    def get_commands(self) -> list[Command]:
        """Get all registered commands from this router."""
        return self._commands.copy()


# Global router instance (convenience)
cli = CliRouter()
