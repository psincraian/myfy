"""
Database session management.

Provides async session factory and context managers for database operations.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Note: AsyncIterator is still used by session_context method


class SessionFactory:
    """
    Factory for creating async database sessions.

    This class wraps SQLAlchemy's async_sessionmaker and provides
    a clean interface for session creation.
    """

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]):
        """
        Initialize session factory.

        Args:
            sessionmaker: SQLAlchemy async sessionmaker instance
        """
        self._sessionmaker = sessionmaker

    def create_session(self) -> AsyncSession:
        """
        Create a new async session.

        Returns:
            AsyncSession instance
        """
        return self._sessionmaker()

    @asynccontextmanager
    async def session_context(self) -> AsyncIterator[AsyncSession]:
        """
        Context manager for automatic session lifecycle.

        Automatically commits on success, rolls back on exception,
        and closes the session in all cases.

        Example:
            async with session_factory.session_context() as session:
                result = await session.execute(query)
                await session.commit()

        Yields:
            AsyncSession instance
        """
        session = self.create_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_session_for_request(session_factory: SessionFactory) -> AsyncSession:
    """
    Dependency provider for REQUEST-scoped database sessions.

    This function is registered as a REQUEST-scoped provider in the DI container.
    Each HTTP request gets its own session. The session lifecycle (commit/rollback/close)
    is managed by the ASGI adapter via cleanup callbacks.

    Args:
        session_factory: SessionFactory injected from DI container

    Returns:
        AsyncSession instance for the current request
    """
    return session_factory.create_session()
