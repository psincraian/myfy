"""
Command representation for CLI commands.

Provides dataclasses for representing registered CLI commands,
similar to Route for web handlers.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommandArg:
    """
    Represents a positional command argument.

    Positional arguments are required values passed to commands
    in order, without flags.

    Example:
        myfy app import-data users.csv
        # 'users.csv' is a positional argument
    """

    name: str
    type_hint: type
    default: Any = None
    help: str | None = None
    is_required: bool = True


@dataclass
class CommandOption:
    """
    Represents a command option (flag).

    Options are named values passed with -- or - prefixes.

    Example:
        myfy app seed-users --count 20 -f
        # --count is an option with value, -f is a boolean flag
    """

    name: str
    type_hint: type
    default: Any = None
    help: str | None = None
    short: str | None = None  # e.g., "-c" for "--count"


@dataclass
class Command:
    """
    Represents a registered CLI command.

    Stores metadata needed for handler injection and execution,
    similar to Route for web handlers.

    Attributes:
        name: Command name (e.g., "seed-users")
        handler: The async/sync function to execute
        group: Optional group name (e.g., "db" for "db:seed")
        help: Help text (typically from docstring)
        arguments: Positional arguments
        options: Named options/flags
        dependencies: Parameter names that need DI injection
    """

    name: str
    handler: Callable[..., Any]
    group: str | None = None
    help: str | None = None

    # Parameter analysis (populated during registration)
    arguments: list[CommandArg] = field(default_factory=list)
    options: list[CommandOption] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        """
        Full command name including group.

        Examples:
            - "seed-users" (no group)
            - "db:seed" (with group)
        """
        if self.group:
            return f"{self.group}:{self.name}"
        return self.name

    def __repr__(self) -> str:
        handler_name = getattr(self.handler, "__name__", "<lambda>")
        return f"Command({self.full_name} -> {handler_name})"
