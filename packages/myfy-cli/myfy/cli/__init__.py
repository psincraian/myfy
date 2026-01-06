"""
CLI module for myfy applications.

Provides a decorator-based API for defining CLI commands with DI integration.

Example:
    ```python
    from myfy.cli import CliModule, command

    @command
    async def seed_db(db: Database, count: int = 100) -> None:
        \"\"\"Seed the database with test data.\"\"\"
        for i in range(count):
            await db.create_record(...)
        print(f"Created {count} records")

    # Add to application
    app = Application()
    app.add_module(CliModule())
    ```

Usage:
    myfy app seed-db --count 200
"""

from .command import Command
from .decorator import command, group
from .extensions import ICommandProvider
from .module import CliModule
from .registry import CommandRegistry

__all__ = [
    "CliModule",
    "Command",
    "CommandRegistry",
    "ICommandProvider",
    "command",
    "group",
]
