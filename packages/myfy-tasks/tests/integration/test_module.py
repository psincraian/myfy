"""Integration tests for TasksModule lifecycle."""

import importlib

import pytest
from sqlalchemy import text

from myfy.tasks import TasksModule, TasksSettings
from myfy.tasks.errors import TasksModuleNotConfiguredError
from myfy.tasks.task import _get_queue, _get_session_factory

# Import the task module itself to access module-level globals for testing
_task_module = importlib.import_module("myfy.tasks.task")


class TestTasksModuleLifecycle:
    """Tests for TasksModule lifecycle management."""

    @pytest.mark.asyncio
    async def test_module_creates_tables_on_start(self, test_db):
        """Test that auto_create_tables=True creates the myfy_tasks table."""
        from sqlalchemy.ext.asyncio import AsyncEngine

        from myfy.core.di import SINGLETON, Container

        data_module, session_factory = test_db

        # Create module with auto_create_tables
        settings = TasksSettings(table_name="myfy_tasks")
        module = TasksModule(settings=settings, auto_create_tables=True)

        # Setup container
        container = Container()
        container.register(type(session_factory), lambda: session_factory, scope=SINGLETON)

        engine = session_factory._sessionmaker.kw.get("bind")
        if engine:
            container.register(AsyncEngine, lambda: engine, scope=SINGLETON)

        # Lifecycle
        module.configure(container)
        container.compile()
        module.finalize(container)
        await module.start()

        try:
            # Verify table exists
            async with engine.begin() as conn:
                # Check table exists using raw SQL (works with SQLite)
                result = await conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='myfy_tasks'")
                )
                tables = result.fetchall()
                assert len(tables) == 1
                assert tables[0][0] == "myfy_tasks"
        finally:
            await module.stop()

    @pytest.mark.asyncio
    async def test_module_configures_task_queue(self, test_db):
        """Test that module sets up _task_queue and _session_factory globals."""
        from sqlalchemy.ext.asyncio import AsyncEngine

        from myfy.core.di import SINGLETON, Container

        data_module, session_factory = test_db

        settings = TasksSettings()
        module = TasksModule(settings=settings, auto_create_tables=True)

        container = Container()
        container.register(type(session_factory), lambda: session_factory, scope=SINGLETON)

        engine = session_factory._sessionmaker.kw.get("bind")
        if engine:
            container.register(AsyncEngine, lambda: engine, scope=SINGLETON)

        module.configure(container)
        container.compile()
        module.finalize(container)
        await module.start()

        try:
            # After start, globals should be set
            queue = _get_queue()
            assert queue is not None

            sf = _get_session_factory()
            assert sf is not None
        finally:
            await module.stop()

    @pytest.mark.asyncio
    async def test_module_provides_queue_accessor(self, task_runner):
        """Test that module.get_queue() returns the task queue."""
        queue = task_runner.module.get_queue()
        assert queue is not None
        assert queue is task_runner.queue


class TestTasksModuleRequirements:
    """Tests for module dependencies and requirements."""

    def test_module_requires_data_module(self):
        """Test that TasksModule declares DataModule dependency."""
        from myfy.data import DataModule

        module = TasksModule()
        assert DataModule in module.requires

    def test_module_provides_task_provider(self):
        """Test that TasksModule provides ITaskProvider."""
        from myfy.tasks.extensions import ITaskProvider

        module = TasksModule()
        assert ITaskProvider in module.provides


class TestTasksModuleNotConfigured:
    """Tests for error handling when module not configured."""

    def test_get_queue_before_module_start_raises(self):
        """Test that _get_queue() raises before module is started."""
        # Save current state
        old_queue = _task_module._task_queue

        try:
            # Clear the queue reference
            _task_module._task_queue = None

            with pytest.raises(TasksModuleNotConfiguredError) as exc:
                _get_queue()

            assert "TaskQueue" in str(exc.value)
        finally:
            # Restore state
            _task_module._task_queue = old_queue

    def test_get_session_factory_before_module_start_raises(self):
        """Test that _get_session_factory() raises before module is started."""
        # Save current state
        old_sf = _task_module._session_factory

        try:
            # Clear the session factory reference
            _task_module._session_factory = None

            with pytest.raises(TasksModuleNotConfiguredError) as exc:
                _get_session_factory()

            assert "SessionFactory" in str(exc.value)
        finally:
            # Restore state
            _task_module._session_factory = old_sf


class TestTasksModuleSettings:
    """Tests for TasksModule settings configuration."""

    def test_default_settings(self):
        """Test that default settings are applied."""
        settings = TasksSettings()

        assert settings.poll_interval == 1.0
        assert settings.worker_concurrency == 4
        assert settings.default_max_retries == 3
        assert settings.task_timeout == 300.0
        assert settings.table_name == "myfy_tasks"

    def test_custom_settings(self):
        """Test that custom settings are applied."""
        settings = TasksSettings(
            poll_interval=0.5,
            worker_concurrency=8,
            default_max_retries=5,
            task_timeout=600.0,
            table_name="custom_tasks",
        )

        assert settings.poll_interval == 0.5
        assert settings.worker_concurrency == 8
        assert settings.default_max_retries == 5
        assert settings.task_timeout == 600.0
        assert settings.table_name == "custom_tasks"

    @pytest.mark.asyncio
    async def test_module_uses_custom_settings(self, test_db):
        """Test that module respects custom settings."""
        from sqlalchemy.ext.asyncio import AsyncEngine

        from myfy.core.di import SINGLETON, Container

        data_module, session_factory = test_db

        custom_settings = TasksSettings(
            default_max_retries=10,
            claim_batch_size=50,
        )
        module = TasksModule(settings=custom_settings, auto_create_tables=True)

        container = Container()
        container.register(type(session_factory), lambda: session_factory, scope=SINGLETON)

        engine = session_factory._sessionmaker.kw.get("bind")
        if engine:
            container.register(AsyncEngine, lambda: engine, scope=SINGLETON)

        module.configure(container)
        container.compile()
        module.finalize(container)
        await module.start()

        try:
            queue = module.get_queue()
            # Settings should be reflected in queue behavior
            assert queue._settings.default_max_retries == 10
            assert queue._settings.claim_batch_size == 50
        finally:
            await module.stop()
