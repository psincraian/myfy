"""Database configuration and session management."""

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from myfy.core import Module


class Base(DeclarativeBase):
    """Base class for all database models."""


class DatabaseModule(Module):
    """Module for database configuration and session management."""

    name = "database"

    def __init__(self, database_url: str):
        """Initialize the database module.

        Args:
            database_url: Database connection URL (should start with postgresql+asyncpg://)
        """
        super().__init__()
        self.database_url = database_url
        self.engine = None
        self.session_maker = None
        self._container = None

    def configure(self, container) -> None:
        """Configure the database module and register session maker."""
        # Store container reference for later use
        self._container = container

        # Register a factory that will lazily create the session maker
        def get_session_maker() -> async_sessionmaker:
            if not self.session_maker:
                raise RuntimeError("Database module not started yet")
            return self.session_maker

        container.register(async_sessionmaker, factory=get_session_maker)

    async def start(self) -> None:
        """Start the database engine and create session maker."""
        self.engine = create_async_engine(
            self.database_url,
            echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
            pool_pre_ping=True,
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            pool_recycle=3600,  # Recycle connections every hour
            pool_timeout=30,  # Wait 30s for connection
        )
        self.session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def stop(self) -> None:
        """Dispose of the database engine."""
        if self.engine:
            await self.engine.dispose()


async def get_db_session(session_maker: async_sessionmaker) -> AsyncSession:
    """Get a database session.

    This is a factory function that can be injected into routes.

    Args:
        session_maker: The session maker from DI container

    Returns:
        An async database session
    """
    async with session_maker() as session:
        yield session
