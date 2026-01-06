"""
Command representation for CLI commands.

Stores metadata about registered commands including handler, parameters,
and DI dependencies.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, get_type_hints


@dataclass
class ParamInfo:
    """Information about a command parameter."""

    name: str
    type_hint: type | None
    default: Any
    is_required: bool
    is_flag: bool = False
    help_text: str | None = None
    alias: str | None = None

    @property
    def cli_name(self) -> str:
        """Get the CLI-friendly name (kebab-case)."""
        return self.name.replace("_", "-")


@dataclass
class Command:
    """
    Represents a registered CLI command.

    Stores metadata needed for CLI argument parsing and DI injection.
    """

    handler: Callable[..., Any] | Callable[..., Awaitable[Any]]
    name: str
    help_text: str | None = None
    group: str | None = None
    cli_params: list[ParamInfo] = field(default_factory=list)
    di_params: list[str] = field(default_factory=list)
    is_async: bool = False

    def __post_init__(self) -> None:
        """Analyze handler signature after initialization."""
        self._analyze_handler()

    def _analyze_handler(self) -> None:
        """
        Analyze handler signature to determine CLI params vs DI dependencies.

        Parameters are classified as:
        1. CLI params: Have type hints of primitive types (str, int, bool, float)
           or have defaults that are primitive values
        2. DI dependencies: Everything else (complex types resolved from container)
        """
        sig = inspect.signature(self.handler)

        # Get type hints, handling forward references
        try:
            hints = get_type_hints(self.handler)
        except Exception:
            hints = {}

        # Check if handler is async
        self.is_async = inspect.iscoroutinefunction(self.handler)

        # CLI-friendly primitive types
        cli_types = (str, int, float, bool)

        for param_name, param in sig.parameters.items():
            # Skip self/cls for methods
            if param_name in ("self", "cls"):
                continue

            param_type = hints.get(param_name)
            default = param.default

            # Determine if this is a CLI param or DI dependency
            is_cli_param = False

            # Check type hint
            if param_type in cli_types:
                is_cli_param = True
            # Check if it's Optional[primitive]
            elif hasattr(param_type, "__origin__"):
                # Handle Optional, Union, etc.
                args = getattr(param_type, "__args__", ())
                if any(arg in cli_types for arg in args):
                    is_cli_param = True
            # Check default value type
            elif default is not inspect.Parameter.empty:
                if isinstance(default, cli_types):
                    is_cli_param = True
                elif default is None:
                    # None default with no clear type - could be either
                    # Treat as CLI param if name suggests it
                    is_cli_param = True

            if is_cli_param:
                # This is a CLI parameter
                is_required = default is inspect.Parameter.empty
                is_flag = param_type is bool or isinstance(default, bool)

                self.cli_params.append(
                    ParamInfo(
                        name=param_name,
                        type_hint=param_type,
                        default=default if default is not inspect.Parameter.empty else None,
                        is_required=is_required,
                        is_flag=is_flag,
                    )
                )
            else:
                # This is a DI dependency
                self.di_params.append(param_name)

    @property
    def full_name(self) -> str:
        """Get the full command name including group prefix."""
        if self.group:
            return f"{self.group}:{self.name}"
        return self.name

    def __repr__(self) -> str:
        params = ", ".join(p.name for p in self.cli_params)
        deps = ", ".join(self.di_params)
        return f"Command({self.name}, params=[{params}], deps=[{deps}])"
