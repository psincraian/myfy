"""
myfy-data: Database/ORM module for myfy framework.

Provides async SQLAlchemy integration with REQUEST-scoped sessions,
connection pooling, and Alembic migrations.

Usage:
    from myfy.data import DataModule, DatabaseSettings
    from myfy.core import Application
    from sqlalchemy.ext.asyncio import AsyncSession

    app = Application()
    app.add_module(DataModule())

    @route.get("/users/{user_id}")
    async def get_user(user_id: int, session: AsyncSession) -> dict:
        # session is automatically injected and cleaned up
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        return {"id": user.id, "name": user.name}

Testing:
    from myfy.data.testing import test_database

    @pytest.mark.asyncio
    async def test_create_user():
        async with test_database() as (module, factory):
            async with factory.session_context() as session:
                user = User(name="Test")
                session.add(user)
"""

from sqlalchemy import Column, Integer, String, Table, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import declarative_base

from .config import SUPPORTED_ASYNC_DRIVERS, DatabaseSettings
from .errors import (
    AutoCreateTablesProductionError,
    DatabaseConnectionError,
    DataModuleError,
    DataModuleNotConfiguredError,
    InvalidDatabaseURLError,
)
from .extensions import IDataProvider
from .migrations import MigrationManager, create_alembic_env_template
from .module import DataModule, data_module
from .session import SessionFactory, get_session_for_request
from .version import __version__

# Re-export commonly used SQLAlchemy constructs for convenience
Base = declarative_base()

__all__ = [
    "SUPPORTED_ASYNC_DRIVERS",
    "AsyncEngine",
    "AsyncSession",
    "AutoCreateTablesProductionError",
    "Base",
    "Column",
    "DataModule",
    "DataModuleError",
    "DataModuleNotConfiguredError",
    "DatabaseConnectionError",
    "DatabaseSettings",
    "IDataProvider",
    "Integer",
    "InvalidDatabaseURLError",
    "MigrationManager",
    "SessionFactory",
    "String",
    "Table",
    "__version__",
    "create_alembic_env_template",
    "data_module",
    "get_session_for_request",
    "select",
]
