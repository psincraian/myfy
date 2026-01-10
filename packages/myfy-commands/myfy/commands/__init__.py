"""
myfy CLI commands module.

Provides user-defined CLI command capabilities for myfy applications.

Quick Start:
    ```python
    from myfy.core import Application
    from myfy.commands import CliModule, cli

    # Define a command
    @cli.command()
    async def seed_users(user_service: UserService, count: int = 10):
        '''Seed the database with test users.'''
        for i in range(count):
            await user_service.create(f"user{i}@example.com")
        print(f"Created {count} users")

    # Register the module
    app = Application()
    app.add_module(CliModule())

    # Run with: myfy app seed-users --count 20
    ```

Command Groups:
    ```python
    from myfy.commands import cli

    # Create a command group
    db = cli.group("db")

    @db.command()
    async def seed(db: Database):
        '''Seed the database.'''
        await db.seed()

    @db.command()
    async def reset(db: Database, force: bool = False):
        '''Reset the database.'''
        if force:
            await db.reset()

    # Run with: myfy app db:seed
    #           myfy app db:reset --force
    ```

Typer Integration:
    ```python
    import typer
    from myfy.commands import cli

    @cli.command()
    async def import_data(
        db: Database,  # DI injection
        file: str = typer.Argument(..., help="Path to import file"),
        dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Simulate import"),
    ):
        '''Import data from a file.'''
        ...
    ```

Available at:
- cli: Global CliRouter for @cli.command() decorator
- CliModule: Module to register with Application
- CliSettings: Configuration class (env prefix: MYFY_CLI_)
- CommandRegistry: Registry of all registered commands
- Command: Command dataclass
"""

from .command import Command, CommandArg, CommandOption
from .config import CliSettings
from .errors import (
    CommandAlreadyRegisteredError,
    CommandError,
    CommandExecutionError,
    CommandNotFoundError,
)
from .executor import CommandExecutor
from .module import CliModule, cli_module
from .registry import CommandRegistry
from .router import CliRouter, cli
from .version import __version__

__all__ = [
    # Main API
    "cli",
    "CliModule",
    "CliSettings",
    # Router
    "CliRouter",
    # Command types
    "Command",
    "CommandArg",
    "CommandOption",
    # Registry
    "CommandRegistry",
    # Executor
    "CommandExecutor",
    # Errors
    "CommandError",
    "CommandNotFoundError",
    "CommandAlreadyRegisteredError",
    "CommandExecutionError",
    # Module instance for entry points
    "cli_module",
    # Version
    "__version__",
]
