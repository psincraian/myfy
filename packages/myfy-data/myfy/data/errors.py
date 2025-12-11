"""
Domain-specific exceptions for DataModule.

Provides clear, actionable error messages following Principle #18:
"Friendly errors and docs - Misconfigurations fail fast with clear, actionable messages."
"""

from __future__ import annotations

from typing import ClassVar


def _mask_password(url: str) -> str:
    """Mask password in database URL for safe logging."""
    if "@" not in url:
        return url
    try:
        parts = url.split("@")
        creds = parts[0].split("://")[1]
        if ":" in creds:
            user = creds.split(":")[0]
            return url.replace(creds, f"{user}:***")
    except (IndexError, ValueError):
        pass
    return url


class DataModuleError(Exception):
    """Base exception for DataModule errors."""


class DataModuleNotConfiguredError(DataModuleError):
    """Raised when module operations are called before configure().

    This error indicates that a DataModule method was called before
    the module was properly initialized. Ensure Application.initialize()
    is called before accessing DataModule resources.
    """

    def __init__(self, resource: str) -> None:
        super().__init__(
            f"{resource} not initialized. "
            "Ensure DataModule.configure() was called during application initialization. "
            "If using Application, call app.initialize() first."
        )
        self.resource = resource


class DatabaseConnectionError(DataModuleError):
    """Raised when database connection fails during startup.

    This error typically indicates one of:
    - Database server is not running
    - Invalid credentials in database URL
    - Network connectivity issues
    - Invalid database URL format
    """

    def __init__(self, url: str, cause: Exception) -> None:
        masked_url = _mask_password(url)
        super().__init__(
            f"Failed to connect to database at {masked_url}: {cause}. "
            "Check that the database server is running and credentials are correct."
        )
        self.url = url
        self.masked_url = masked_url
        self.__cause__ = cause


class InvalidDatabaseURLError(DataModuleError):
    """Raised when database URL has an unsupported scheme.

    Supported database URL schemes:
    - sqlite+aiosqlite:// (SQLite with async driver)
    - postgresql+asyncpg:// (PostgreSQL with asyncpg)
    - mysql+aiomysql:// (MySQL with aiomysql)
    """

    SUPPORTED_SCHEMES: ClassVar[list[str]] = [
        "sqlite+aiosqlite",
        "postgresql+asyncpg",
        "mysql+aiomysql",
    ]

    def __init__(self, url: str) -> None:
        masked_url = _mask_password(url)
        schemes = ", ".join(self.SUPPORTED_SCHEMES)
        super().__init__(
            f"Unsupported database URL: {masked_url}. "
            f"Supported schemes: {schemes}. "
            "Ensure you're using an async-compatible driver."
        )
        self.url = url
        self.masked_url = masked_url


class AutoCreateTablesProductionError(DataModuleError):
    """Raised when auto_create_tables is used in production environment.

    auto_create_tables=True is designed for development and testing only.
    In production, you should use Alembic migrations for controlled schema changes.

    To fix this error:
    1. Set MYFY_DATA_ENVIRONMENT to 'development' or 'test', OR
    2. Use Alembic migrations instead of auto_create_tables, OR
    3. Remove auto_create_tables=True from DataModule configuration
    """

    def __init__(self) -> None:
        super().__init__(
            "auto_create_tables=True is not allowed in production environment. "
            "Use Alembic migrations for production schema management. "
            "Set MYFY_DATA_ENVIRONMENT='development' or 'test' to enable auto_create_tables."
        )
