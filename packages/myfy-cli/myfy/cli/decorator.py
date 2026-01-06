"""
Decorators for defining CLI commands.

Provides the @command decorator that registers functions with the CommandRegistry.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar, overload

from .command import Command
from .registry import CommandRegistry

P = ParamSpec("P")
R = TypeVar("R")


@overload
def command(func: Callable[P, R]) -> Callable[P, R]: ...


@overload
def command(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]: ...


@overload
def command(
    *,
    name: str | None = None,
    help: str | None = None,
    group: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def command(
    func: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    help: str | None = None,
    group: str | None = None,
) -> Any:
    """
    Decorator to define a CLI command.

    Commands are registered in the global CommandRegistry and can be executed
    via `myfy app <command-name>`.

    Parameters can be:
    - CLI arguments: Primitive types (str, int, float, bool) become CLI options
    - DI dependencies: Complex types are resolved from the DI container

    Args:
        func: The function to decorate (when used without parentheses)
        name: Custom command name (default: function name with underscores as dashes)
        help: Help text for the command (default: function docstring)
        group: Group name for organizing commands (e.g., "users", "data")

    Returns:
        The decorated function (unchanged, but registered as a command)

    Example:
        ```python
        # Simple command (name derived from function: "greet")
        @command
        def greet(name: str) -> None:
            \"\"\"Greet a user by name.\"\"\"
            print(f"Hello, {name}!")

        # Command with options
        @command
        def seed_db(count: int = 100, clear: bool = False) -> None:
            \"\"\"Seed the database with test data.\"\"\"
            if clear:
                print("Clearing existing data...")
            print(f"Creating {count} records...")

        # Async command with DI
        @command
        async def create_admin(
            email: str,
            password: str,
            user_service: UserService,  # Injected from DI
        ) -> None:
            \"\"\"Create an admin user.\"\"\"
            await user_service.create_admin(email, password)

        # Custom name and group
        @command(name="run-migrations", group="data")
        async def run_migrations(db: Database) -> None:
            \"\"\"Run pending database migrations.\"\"\"
            await db.migrate()
        ```

    Usage:
        ```bash
        myfy app greet John
        myfy app seed-db --count 200 --clear
        myfy app create-admin admin@example.com secretpass
        myfy app data:run-migrations
        ```
    """

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        # Derive command name from function name if not provided
        cmd_name = name or f.__name__.replace("_", "-")

        # Use docstring as help text if not provided
        help_text = help or f.__doc__

        # Create command instance
        cmd = Command(
            handler=f,
            name=cmd_name,
            help_text=help_text,
            group=group,
        )

        # Register with global registry
        CommandRegistry.get_instance().register(cmd)

        # Return original function unchanged
        return f

    if func is not None:
        # Called without parentheses: @command
        return decorator(func)

    # Called with parentheses: @command(...)
    return decorator


class CommandGroup:
    """
    A group of related commands.

    Created via the @group decorator to organize commands under a common prefix.

    Example:
        ```python
        @group(name="users", help="User management commands")
        class UserCommands:
            @command
            async def create(self, email: str, service: UserService) -> None:
                await service.create(email)

            @command
            async def delete(self, email: str, service: UserService) -> None:
                await service.delete(email)
        ```

    Usage:
        ```bash
        myfy app users:create user@example.com
        myfy app users:delete user@example.com
        ```
    """

    def __init__(self, name: str, help_text: str | None = None) -> None:
        self.name = name
        self.help_text = help_text
        self.commands: list[Command] = []


def group(
    name: str,
    help: str | None = None,
) -> Callable[[type], type]:
    """
    Decorator to create a command group from a class.

    Methods decorated with @command inside the class will be registered
    with the group prefix.

    Args:
        name: Group name (used as prefix, e.g., "users")
        help: Help text for the group

    Returns:
        Class decorator that registers all @command methods with the group

    Example:
        ```python
        @group(name="users", help="User management commands")
        class UserCommands:
            @command
            async def create(email: str, user_service: UserService) -> None:
                \"\"\"Create a new user.\"\"\"
                await user_service.create(email)

            @command
            async def list(user_service: UserService) -> None:
                \"\"\"List all users.\"\"\"
                users = await user_service.list_all()
                for user in users:
                    print(user.email)
        ```

    Usage:
        ```bash
        myfy app users:create user@example.com
        myfy app users:list
        ```
    """

    def decorator(cls: type) -> type:
        registry = CommandRegistry.get_instance()

        # Iterate over class methods
        for attr_name in dir(cls):
            if attr_name.startswith("_"):
                continue

            attr = getattr(cls, attr_name)
            if not callable(attr):
                continue

            # Check if this method should be a command
            # We need to register it with the group
            cmd_name = attr_name.replace("_", "-")
            help_text = attr.__doc__

            cmd = Command(
                handler=attr,
                name=cmd_name,
                help_text=help_text,
                group=name,
            )

            registry.register(cmd)

        return cls

    return decorator
