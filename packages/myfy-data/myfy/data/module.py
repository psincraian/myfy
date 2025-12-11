"""
Data module for myfy.

Provides database/ORM capabilities with async SQLAlchemy and connection pooling.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from myfy.core.config import load_settings
from myfy.core.di import REQUEST, SINGLETON

from .config import DatabaseSettings
from .errors import (
    AutoCreateTablesProductionError,
    DatabaseConnectionError,
    DataModuleNotConfiguredError,
)
from .extensions import IDataProvider
from .session import SessionFactory, get_session_for_request

if TYPE_CHECKING:
    from myfy.core.di import Container

logger = logging.getLogger(__name__)


class DataModule:
    """
    Data module - provides database/ORM capabilities.

    Features:
    - Async SQLAlchemy 2.0+ integration
    - Connection pooling with configurable settings
    - REQUEST-scoped sessions (one per HTTP request)
    - Alembic migration support
    - Automatic connection lifecycle management
    - Optional auto table creation for development

    Lifecycle (per ADR-0005):
    - configure(): Register services in DI container
    - extend(): No-op (DataModule doesn't extend other modules)
    - finalize(): No-op (engine created during configure)
    - start(): Optionally create tables, then perform database health check
    - stop(): Dispose connection pool
    """

    def __init__(
        self,
        settings: DatabaseSettings | None = None,
        auto_create_tables: bool = False,
        metadata: MetaData | None = None,
    ) -> None:
        """
        Create data module.

        Args:
            settings: Custom database settings (defaults to loading from environment)
            auto_create_tables: If True, automatically create database tables from
                metadata during start(). Only allowed in development/test environments.
                Raises AutoCreateTablesProductionError in production.
            metadata: SQLAlchemy MetaData containing table definitions. Required if
                auto_create_tables=True. Typically pass Base.metadata from your models.

        Example:
            ```python
            from myfy.data import DataModule, Base
            from sqlalchemy import Column, Integer, String

            class User(Base):
                __tablename__ = "users"
                id = Column(Integer, primary_key=True)
                name = Column(String(100))

            app.add_module(DataModule(
                auto_create_tables=True,
                metadata=Base.metadata,
            ))
            ```
        """
        self._settings = settings
        self._auto_create_tables = auto_create_tables
        self._metadata = metadata
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None
        self._session_factory: SessionFactory | None = None

    @property
    def name(self) -> str:
        """Module name for registration."""
        return "data"

    @property
    def requires(self) -> list[type]:
        """
        Module types this module depends on.

        DataModule has no dependencies on other modules.
        Implements ADR-0005 module dependency declaration.
        """
        return []

    @property
    def provides(self) -> list[type]:
        """
        Extension protocols provided by this module.

        Implements ADR-0005 module extension points.
        """
        return [IDataProvider]

    def configure(self, container: Container) -> None:
        """
        Configure data module.

        Registers DatabaseSettings, AsyncEngine, SessionFactory, and AsyncSession
        in the DI container.

        Note: In nested settings pattern (ADR-0007), DatabaseSettings is registered
        by Application. Otherwise, load standalone DatabaseSettings.
        """
        from myfy.core.di.types import ProviderKey  # noqa: PLC0415

        logger.debug("Configuring DataModule...")

        # Check if DatabaseSettings already registered (from nested app settings)
        key = ProviderKey(DatabaseSettings)
        if key not in container._providers:
            # Load standalone DatabaseSettings
            if self._settings is None:
                self._settings = load_settings(DatabaseSettings)
            container.register(
                type_=DatabaseSettings,
                factory=lambda: self._settings,
                scope=SINGLETON,
            )
            logger.debug("Registered standalone DatabaseSettings")
        else:
            logger.debug("Using nested DatabaseSettings from application")

        # Create engine and sessionmaker
        settings = self._settings or container.get(DatabaseSettings)
        self._engine = self._create_engine(settings)
        self._sessionmaker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self._session_factory = SessionFactory(self._sessionmaker)

        # Register engine as singleton
        container.register(
            type_=AsyncEngine,
            factory=lambda: self._engine,
            scope=SINGLETON,
        )

        # Register session factory as singleton
        container.register(
            type_=SessionFactory,
            factory=lambda: self._session_factory,
            scope=SINGLETON,
        )

        # Register AsyncSession as REQUEST-scoped
        # Each request gets its own session that is automatically cleaned up
        container.register(
            type_=AsyncSession,
            factory=get_session_for_request,
            scope=REQUEST,
        )

        logger.debug("DataModule configured successfully")

    def extend(self, container: Container) -> None:
        """
        Extend other modules' services before container compilation.

        DataModule doesn't need to extend other modules' services.
        This method exists for ADR-0005 lifecycle compliance.

        Args:
            container: DI container (unused)
        """

    def finalize(self, container: Container) -> None:
        """
        Finalize module configuration after container compilation.

        DataModule doesn't need post-compilation configuration as the
        database engine and session factory are created during configure().
        This method exists for ADR-0005 lifecycle compliance.

        Args:
            container: DI container (unused)
        """

    def _create_engine(self, settings: DatabaseSettings) -> AsyncEngine:
        """
        Create async SQLAlchemy engine.

        Args:
            settings: Database settings

        Returns:
            Configured AsyncEngine instance
        """
        # Build engine kwargs
        engine_kwargs: dict = {
            "echo": settings.echo,
            "echo_pool": settings.echo_pool,
            "pool_pre_ping": settings.pool_pre_ping,
        }

        # Add pool configuration (not applicable for SQLite)
        if not settings.database_url.startswith("sqlite"):
            engine_kwargs.update(
                {
                    "pool_size": settings.pool_size,
                    "max_overflow": settings.max_overflow,
                    "pool_timeout": settings.pool_timeout,
                    "pool_recycle": settings.pool_recycle,
                }
            )
            logger.debug(
                "Configured connection pool: size=%d, max_overflow=%d",
                settings.pool_size,
                settings.max_overflow,
            )

        # Add SQLite-specific configuration
        if settings.database_url.startswith("sqlite"):
            engine_kwargs["connect_args"] = {
                "check_same_thread": settings.sqlite_check_same_thread,
            }
            logger.debug(
                "Configured SQLite with check_same_thread=%s", settings.sqlite_check_same_thread
            )

        return create_async_engine(settings.database_url, **engine_kwargs)

    async def start(self) -> None:
        """
        Start data module.

        If auto_create_tables is enabled, creates database tables from metadata.
        Then performs connection health check to ensure database is accessible.

        Raises:
            DataModuleNotConfiguredError: If configure() was not called
            AutoCreateTablesProductionError: If auto_create_tables used in production
            DatabaseConnectionError: If database connection fails
        """
        if self._engine is None:
            raise DataModuleNotConfiguredError("Engine")

        # Auto-create tables if enabled (before health check)
        if self._auto_create_tables:
            await self._create_tables()

        # Health check
        logger.debug("Performing database connection health check...")
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection established")
        except Exception as e:
            url = self._settings.database_url if self._settings else "unknown"
            raise DatabaseConnectionError(url, e) from e

    async def _create_tables(self) -> None:
        """
        Create database tables from registered metadata.

        Only allowed in development and test environments.

        Raises:
            AutoCreateTablesProductionError: If called in production environment
        """
        # Get settings to check environment
        settings = self._settings
        if settings is None:
            settings = DatabaseSettings()

        # Safety check: block in production
        if settings.environment == "production":
            raise AutoCreateTablesProductionError

        # Warn if no metadata provided
        if self._metadata is None:
            logger.warning(
                "auto_create_tables=True but no metadata provided. "
                "Pass metadata=Base.metadata to DataModule() to create tables."
            )
            return

        # Create tables
        logger.info("Creating database tables from metadata...")
        assert self._engine is not None  # Checked at start() entry
        async with self._engine.begin() as conn:
            await conn.run_sync(self._metadata.create_all)
        logger.info("✅ Database tables created")

    async def stop(self) -> None:
        """
        Stop data module gracefully.

        Closes all database connections and disposes of the connection pool.
        """
        if self._engine is not None:
            logger.debug("Closing database connections...")
            await self._engine.dispose()
            logger.info("✅ Database connections closed")

    # IDataProvider protocol implementation

    def get_engine(self) -> AsyncEngine:
        """
        Get the SQLAlchemy async engine.

        Returns:
            AsyncEngine instance

        Raises:
            DataModuleNotConfiguredError: If engine not initialized
        """
        if self._engine is None:
            raise DataModuleNotConfiguredError("Engine")
        return self._engine

    def get_session_factory(self) -> SessionFactory:
        """
        Get the session factory.

        Returns:
            SessionFactory instance for creating database sessions

        Raises:
            DataModuleNotConfiguredError: If session factory not initialized
        """
        if self._session_factory is None:
            raise DataModuleNotConfiguredError("SessionFactory")
        return self._session_factory

    def __repr__(self) -> str:
        """String representation of module."""
        if self._settings:
            # Mask password in URL for security
            url = self._settings.database_url
            if "@" in url:
                parts = url.split("@")
                creds = parts[0].split("://")[1]
                if ":" in creds:
                    user = creds.split(":")[0]
                    masked_url = url.replace(creds, f"{user}:***")
                else:
                    masked_url = url
            else:
                masked_url = url
            return f"DataModule(url={masked_url})"
        return "DataModule()"


# Module instance for entry point
data_module = DataModule()
