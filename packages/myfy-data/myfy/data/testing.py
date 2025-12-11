"""
Test utilities for DataModule.

Provides helper functions and context managers for testing database operations.
Following Principle #19: "Testable by nature - Override dependencies easily,
spin up fake apps in tests, and verify modules in isolation."
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from .config import DatabaseSettings
from .module import DataModule

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
    from sqlalchemy.orm import DeclarativeBase

    from .session import SessionFactory


@asynccontextmanager
async def test_database(
    *,
    database_url: str,
    echo: bool,
) -> AsyncIterator[tuple[DataModule, SessionFactory]]:
    """
    Context manager for testing with an isolated database.

    Creates an in-memory SQLite database by default, perfect for unit tests.
    Automatically handles module lifecycle (configure, start, stop).

    Args:
        database_url: Database URL (defaults to in-memory SQLite)
        echo: Enable SQL logging for debugging

    Yields:
        Tuple of (DataModule, SessionFactory) for test access

    Example:
        ```python
        @pytest.mark.asyncio
        async def test_create_user():
            async with test_database() as (module, session_factory):
                # Create tables
                engine = module.get_engine()
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)

                # Test operations
                async with session_factory.session_context() as session:
                    user = User(name="Test")
                    session.add(user)
                    # auto-commits on exit

                # Verify
                async with session_factory.session_context() as session:
                    result = await session.execute(select(User))
                    users = result.scalars().all()
                    assert len(users) == 1
        ```
    """
    from myfy.core.di import Container  # noqa: PLC0415

    settings = DatabaseSettings(database_url=database_url, echo=echo)
    module = DataModule(settings=settings)
    container = Container()

    module.configure(container)
    await module.start()
    try:
        yield module, module.get_session_factory()
    finally:
        await module.stop()


@asynccontextmanager
async def test_session(
    session_factory: SessionFactory,
) -> AsyncIterator[AsyncSession]:
    """
    Context manager for a test session with automatic cleanup.

    Wraps SessionFactory.session_context() for cleaner test code.

    Args:
        session_factory: SessionFactory from test_database()

    Yields:
        AsyncSession instance

    Example:
        ```python
        async with test_database() as (module, factory):
            async with test_session(factory) as session:
                user = User(name="Test")
                session.add(user)
        ```
    """
    async with session_factory.session_context() as session:
        yield session


async def create_test_tables(
    engine: AsyncEngine,
    base: type[DeclarativeBase],
) -> None:
    """
    Create all tables defined in a declarative base.

    Helper for test setup that creates all model tables.

    Args:
        engine: AsyncEngine from DataModule
        base: SQLAlchemy declarative base class with model definitions

    Example:
        ```python
        async with test_database() as (module, factory):
            await create_test_tables(module.get_engine(), Base)
            # Tables now exist
        ```
    """
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)


async def drop_test_tables(
    engine: AsyncEngine,
    base: type[DeclarativeBase],
) -> None:
    """
    Drop all tables defined in a declarative base.

    Helper for test teardown that removes all model tables.

    Args:
        engine: AsyncEngine from DataModule
        base: SQLAlchemy declarative base class with model definitions

    Example:
        ```python
        async with test_database() as (module, factory):
            await create_test_tables(module.get_engine(), Base)
            # ... run tests ...
            await drop_test_tables(module.get_engine(), Base)
        ```
    """
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.drop_all)


class TestDatabaseFixture:
    """
    Pytest fixture helper for database testing.

    Provides a reusable fixture pattern for pytest with proper setup/teardown.

    Example:
        ```python
        # conftest.py
        import pytest
        from myfy.data.testing import TestDatabaseFixture

        @pytest.fixture
        async def db_fixture():
            fixture = TestDatabaseFixture()
            async with fixture.setup() as (module, factory):
                yield fixture

        # test_models.py
        @pytest.mark.asyncio
        async def test_user_creation(db_fixture):
            async with db_fixture.session() as session:
                user = User(name="Test")
                session.add(user)
        ```
    """

    def __init__(
        self,
        database_url: str = "sqlite+aiosqlite:///:memory:",
        echo: bool = False,
    ) -> None:
        """
        Initialize test fixture.

        Args:
            database_url: Database URL (defaults to in-memory SQLite)
            echo: Enable SQL logging
        """
        self.database_url = database_url
        self.echo = echo
        self._module: DataModule | None = None
        self._session_factory: SessionFactory | None = None

    @asynccontextmanager
    async def setup(self) -> AsyncIterator[tuple[DataModule, SessionFactory]]:
        """
        Setup the test database.

        Yields:
            Tuple of (DataModule, SessionFactory)
        """
        async with test_database(
            database_url=self.database_url,
            echo=self.echo,
        ) as (module, factory):
            self._module = module
            self._session_factory = factory
            yield module, factory

    @property
    def module(self) -> DataModule:
        """Get the DataModule instance."""
        if self._module is None:
            msg = "Fixture not set up. Use 'async with fixture.setup()' first."
            raise RuntimeError(msg)
        return self._module

    @property
    def session_factory(self) -> SessionFactory:
        """Get the SessionFactory instance."""
        if self._session_factory is None:
            msg = "Fixture not set up. Use 'async with fixture.setup()' first."
            raise RuntimeError(msg)
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """
        Get a test session.

        Yields:
            AsyncSession instance
        """
        async with test_session(self.session_factory) as session:
            yield session
