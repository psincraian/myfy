"""
Extension protocols for DataModule.

These protocols define contracts for modules that want to extend
or integrate with the database functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

    from .session import SessionFactory


@runtime_checkable
class IDataProvider(Protocol):
    """
    Protocol for modules that provide database access.

    Modules implementing this protocol indicate they offer database
    connectivity and session management. This protocol is primarily
    used for module dependency declaration (ADR-0005).

    Example:
        class DataModule:
            @property
            def provides(self) -> list[type]:
                return [IDataProvider]

            def get_engine(self) -> AsyncEngine:
                return self._engine

            def get_session_factory(self) -> SessionFactory:
                return self._session_factory
    """

    def get_engine(self) -> AsyncEngine:
        """
        Get the SQLAlchemy async engine.

        Returns:
            AsyncEngine instance for database operations
        """
        ...

    def get_session_factory(self) -> SessionFactory:
        """
        Get the session factory.

        Returns:
            SessionFactory instance for creating database sessions
        """
        ...
