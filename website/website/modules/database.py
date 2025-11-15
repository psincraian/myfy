"""Database configuration and session management module."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from myfy.core import SINGLETON, Container, Module

from ..config import DatabaseSettings


class DatabaseModule(Module):
    """Module for database configuration and session management.

    This module provides database connectivity and session management
    for the application. It creates an async SQLAlchemy engine and
    registers the session maker in the DI container.

    Lifecycle:
        - configure(): Register session maker factory in DI
        - start(): Create database engine and session maker
        - stop(): Dispose database engine
    """

    name = "database"

    def __init__(self):
        """Initialize the database module."""
        super().__init__()
        self.engine = None
        self.session_maker = None
        self._container: Container | None = None

    def configure(self, container: Container) -> None:
        """Configure the database module and register session maker.

        Args:
            container: DI container to register services
        """
        # Store container reference for later use
        self._container = container

        # Register a factory that will lazily create the session maker
        def get_session_maker() -> async_sessionmaker:
            if not self.session_maker:
                raise RuntimeError("Database module not started yet")
            return self.session_maker

        container.register(async_sessionmaker, factory=get_session_maker, scope=SINGLETON)

    def finalize(self, container: Container) -> None:
        """Finalize the database module after container compilation.

        This is called after the container is compiled, so we can safely
        retrieve settings.

        Args:
            container: DI container (now compiled)
        """
        # Get database settings from container (will be used in start())
        # Store it for later use in start()
        # Settings will be retrieved in start() method

    async def start(self) -> None:
        """Start the database engine and create session maker.

        This method is called during application startup to initialize
        the database connection pool.
        """
        if not self._container:
            raise RuntimeError("Database module not configured")

        # Get database settings from container (auto-injected from AppSettings)
        settings = self._container.get(DatabaseSettings)

        self.engine = create_async_engine(
            settings.url,
            echo=settings.echo,
            pool_pre_ping=True,
            pool_size=settings.pool_size,
            max_overflow=settings.max_overflow,
            pool_recycle=settings.pool_recycle,
            pool_timeout=settings.pool_timeout,
        )
        self.session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def stop(self) -> None:
        """Dispose of the database engine.

        This method is called during application shutdown to properly
        close database connections.
        """
        if self.engine:
            await self.engine.dispose()


async def get_db_session(session_maker: async_sessionmaker) -> AsyncGenerator[AsyncSession, None]:
    """Get a database session.

    This is a factory function that can be injected into routes.

    Args:
        session_maker: The session maker from DI container

    Yields:
        An async database session
    """
    async with session_maker() as session:
        yield session
