"""
Custom exceptions for CLI commands module.

Provides specific error types for command-related failures.
"""


class CommandError(Exception):
    """Base exception for command-related errors."""

    pass


class CommandNotFoundError(CommandError):
    """Raised when a command is not found in the registry."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Command not found: {name}")


class CommandAlreadyRegisteredError(CommandError):
    """Raised when attempting to register a command that already exists."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Command already registered: {name}")


class CommandExecutionError(CommandError):
    """Raised when command execution fails."""

    def __init__(self, name: str, cause: Exception) -> None:
        self.name = name
        self.cause = cause
        super().__init__(f"Command '{name}' failed: {cause}")
