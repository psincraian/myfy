"""
Database migration support using Alembic.

Provides helpers for initializing and running database migrations.
"""

import subprocess
import sys
from pathlib import Path


class MigrationManager:
    """
    Manager for Alembic database migrations.

    Provides a programmatic interface to Alembic commands for
    schema versioning and migrations.
    """

    def __init__(self, alembic_dir: Path = Path("alembic")):
        """
        Initialize migration manager.

        Args:
            alembic_dir: Directory containing alembic.ini and versions/
        """
        self.alembic_dir = alembic_dir
        self.alembic_ini = alembic_dir.parent / "alembic.ini"

    def _run_alembic(self, *args: str) -> None:
        """
        Run alembic command using Python module.

        Uses `sys.executable -m alembic` to ensure the correct
        Python environment is used.

        Args:
            *args: Arguments to pass to alembic
        """
        cmd = [sys.executable, "-m", "alembic", *args]
        subprocess.run(cmd, check=True)

    def init(self) -> None:
        """
        Initialize Alembic in the current project.

        Creates alembic.ini and alembic/ directory structure.
        """
        self._run_alembic("init", str(self.alembic_dir))

    def revision(self, message: str, autogenerate: bool = True) -> None:
        """
        Create a new migration revision.

        Args:
            message: Description of the migration
            autogenerate: Whether to auto-detect schema changes
        """
        args = ["revision", "-m", message]
        if autogenerate:
            args.append("--autogenerate")
        self._run_alembic(*args)

    def upgrade(self, revision: str = "head") -> None:
        """
        Upgrade database to a specific revision.

        Args:
            revision: Target revision (default: 'head' for latest)
        """
        self._run_alembic("upgrade", revision)

    def downgrade(self, revision: str = "-1") -> None:
        """
        Downgrade database to a previous revision.

        Args:
            revision: Target revision (default: '-1' for one step back)
        """
        self._run_alembic("downgrade", revision)

    def current(self) -> None:
        """Display current revision."""
        self._run_alembic("current")

    def history(self) -> None:
        """Display migration history."""
        self._run_alembic("history")


def create_alembic_env_template(database_url: str) -> str:
    """
    Generate Alembic env.py template for async engines.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        Content for alembic/env.py file
    """
    return f'''"""Alembic environment configuration for myfy-data."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
# from myapp.models import Base
# target_metadata = Base.metadata
target_metadata = None

# Override database URL from settings if needed
config.set_main_option("sqlalchemy.url", "{database_url}")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={{"paramstyle": "named"}},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with given connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {{}}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
