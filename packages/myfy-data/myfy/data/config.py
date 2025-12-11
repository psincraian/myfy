"""
Database module configuration.

Each module defines its own settings for modularity (ADR-0002).
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import SettingsConfigDict

from myfy.core.config import BaseSettings

# Supported async database drivers
SUPPORTED_ASYNC_DRIVERS = [
    "sqlite+aiosqlite",
    "postgresql+asyncpg",
    "mysql+aiomysql",
]


class DatabaseSettings(BaseSettings):
    """
    Database module settings.

    Configure database connection, connection pooling, and SQLAlchemy engine options.

    Environment variables use the MYFY_DATA_ prefix:
    - MYFY_DATA_DATABASE_URL
    - MYFY_DATA_POOL_SIZE
    - MYFY_DATA_MAX_OVERFLOW
    - etc.

    Example:
        ```python
        # Via environment
        export MYFY_DATA_DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db"

        # Via code
        settings = DatabaseSettings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            pool_size=10,
        )
        ```
    """

    # Connection configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./myfy.db",
        description="SQLAlchemy database URL (e.g., 'postgresql+asyncpg://user:pass@localhost/db')",
    )

    # Connection pool configuration
    pool_size: int = Field(
        default=5,
        description="Number of connections to maintain in the pool",
        ge=1,
    )
    max_overflow: int = Field(
        default=10,
        description="Maximum number of connections to create beyond pool_size",
        ge=0,
    )
    pool_timeout: float = Field(
        default=30.0,
        description="Seconds to wait before timing out on getting a connection",
        ge=0,
    )
    pool_recycle: int = Field(
        default=3600,
        description="Seconds after which connections are recycled (prevents stale connections)",
        ge=-1,
    )
    pool_pre_ping: bool = Field(
        default=True,
        description="Test connections before using them to detect disconnected connections",
    )

    # Engine configuration
    echo: bool = Field(
        default=False,
        description="Log all SQL statements (useful for debugging)",
    )
    echo_pool: bool = Field(
        default=False,
        description="Log connection pool checkouts/checkins",
    )

    # SQLite-specific configuration
    sqlite_check_same_thread: bool = Field(
        default=False,
        description="SQLite check_same_thread parameter (set False for async SQLite)",
    )

    # Environment configuration (for auto_create_tables safety)
    environment: str = Field(
        default="development",
        description="Environment name (development, test, production). "
        "Used by auto_create_tables to prevent accidental schema changes in production.",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """
        Validate database URL uses a supported async driver.

        Raises:
            ValueError: If URL doesn't use a supported async driver
        """
        # Check if URL starts with any supported driver
        if not any(v.startswith(driver) for driver in SUPPORTED_ASYNC_DRIVERS):
            # Extract the scheme for better error message
            scheme = v.split("://")[0] if "://" in v else v
            supported = ", ".join(SUPPORTED_ASYNC_DRIVERS)
            msg = (
                f"Unsupported database URL scheme: '{scheme}'. "
                f"Supported async drivers: {supported}. "
                "Note: myfy-data requires async drivers. "
                "Use 'postgresql+asyncpg://' instead of 'postgresql://'."
            )
            raise ValueError(msg)
        return v

    @field_validator("pool_size")
    @classmethod
    def validate_pool_size(cls, v: int) -> int:
        """
        Validate pool_size with helpful error message.

        Note: Pydantic's ge=1 constraint handles validation, but this
        provides a more actionable error message.
        """
        if v < 1:
            msg = (
                f"pool_size must be at least 1, got {v}. "
                "For SQLite, pool_size is ignored but must still be >= 1."
            )
            raise ValueError(msg)
        return v

    @field_validator("pool_timeout")
    @classmethod
    def validate_pool_timeout(cls, v: float) -> float:
        """Validate pool_timeout with helpful error message."""
        if v < 0:
            msg = (
                f"pool_timeout must be non-negative, got {v}. "
                "Set to 0 to disable timeout (not recommended for production)."
            )
            raise ValueError(msg)
        return v

    model_config = SettingsConfigDict(env_prefix="MYFY_DATA_")
