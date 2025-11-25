"""
Integration tests for myfy-core Application and Module system.

These tests verify:
- Application initialization flow
- Module lifecycle phases
- Module discovery and ordering
- Settings integration
"""

from typing import cast

import pytest

from myfy.core.di import SINGLETON, Container
from myfy.core.kernel import (
    Application,
    Module,
    ModuleDependencyError,
    MyfyModuleNotFoundError,
)

pytestmark = pytest.mark.integration


# =============================================================================
# Test Modules
# =============================================================================


def as_module(obj: object) -> Module:
    """Cast test module to Module protocol for type checker."""
    return cast("Module", obj)


class DatabaseModule:
    """Module that provides database services."""

    def __init__(self):
        self.configured = False
        self.started = False
        self.stopped = False

    @property
    def name(self) -> str:
        return "database"

    def configure(self, container: Container) -> None:
        self.configured = True
        container.register(
            type_=dict,
            factory=lambda: {"connection": "db://localhost"},
            scope=SINGLETON,
            qualifier="db_config",
        )

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


class CacheModule:
    """Module that provides caching services."""

    def __init__(self):
        self.configured = False

    @property
    def name(self) -> str:
        return "cache"

    @property
    def requires(self) -> list[type]:
        return [DatabaseModule]  # Depends on database

    def configure(self, container: Container) -> None:
        self.configured = True
        container.register(
            type_=dict,
            factory=lambda: {"cache": "redis://localhost"},
            scope=SINGLETON,
            qualifier="cache_config",
        )

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


class ApiModule:
    """Module that provides API endpoints."""

    def __init__(self):
        self.configured = False
        self.extended = False
        self.finalized = False

    @property
    def name(self) -> str:
        return "api"

    @property
    def requires(self) -> list[type]:
        return [DatabaseModule, CacheModule]

    def configure(self, container: Container) -> None:
        self.configured = True

    def extend(self, container: Container) -> None:
        self.extended = True

    def finalize(self, container: Container) -> None:
        self.finalized = True

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


class AnalyticsProtocol:
    """Protocol for analytics services."""


class AnalyticsModule:
    """Module that implements analytics protocol."""

    @property
    def name(self) -> str:
        return "analytics"

    @property
    def provides(self) -> list[type]:
        return [AnalyticsProtocol]

    def configure(self, container: Container) -> None:
        pass

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


# =============================================================================
# Application Initialization Tests
# =============================================================================


class TestApplicationInitialization:
    """Test Application initialization flow."""

    def test_basic_initialization(self):
        """Test basic application initialization."""
        app = Application(auto_discover=False)
        app.add_module(as_module(DatabaseModule()))

        app.initialize()

        assert app._initialized
        assert len(app._modules) == 1

    def test_container_is_compiled_after_init(self):
        """Test that container is compiled after initialization."""
        app = Application(auto_discover=False)
        app.add_module(as_module(DatabaseModule()))

        app.initialize()

        assert app.container._frozen

    def test_modules_are_configured(self):
        """Test that all modules are configured during init."""
        db_module = DatabaseModule()
        cache_module = CacheModule()

        app = Application(auto_discover=False)
        app.add_module(as_module(db_module))
        app.add_module(as_module(cache_module))

        app.initialize()

        assert db_module.configured
        assert cache_module.configured

    def test_double_initialization_is_noop(self):
        """Test that double initialization is safe."""
        db_module = DatabaseModule()
        app = Application(auto_discover=False)
        app.add_module(as_module(db_module))

        app.initialize()
        first_container = app.container

        app.initialize()

        # Container should be the same
        assert app.container is first_container


# =============================================================================
# Module Dependency Tests
# =============================================================================


class TestModuleDependencies:
    """Test module dependency resolution."""

    def test_modules_ordered_by_dependencies(self):
        """Test that modules are sorted by dependency order."""
        app = Application(auto_discover=False)

        # Add in wrong order
        app.add_module(as_module(ApiModule()))  # Depends on DB and Cache
        app.add_module(as_module(CacheModule()))  # Depends on DB
        app.add_module(as_module(DatabaseModule()))

        app.initialize()

        module_names = [m.name for m in app._modules]

        # Database must come before Cache and Api
        db_idx = module_names.index("database")
        cache_idx = module_names.index("cache")
        api_idx = module_names.index("api")

        assert db_idx < cache_idx
        assert db_idx < api_idx
        assert cache_idx < api_idx

    def test_missing_dependency_raises_error(self):
        """Test that missing dependency raises clear error."""
        app = Application(auto_discover=False)
        app.add_module(as_module(CacheModule()))  # Requires DatabaseModule

        with pytest.raises(ModuleDependencyError) as exc_info:
            app.initialize()

        error = exc_info.value
        assert "DatabaseModule" in str(error)

    def test_complex_dependency_graph(self):
        """Test complex dependency graph resolution."""

        class ModuleA:
            @property
            def name(self) -> str:
                return "a"

            def configure(self, container: Container) -> None:
                pass

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass

        class ModuleB:
            @property
            def name(self) -> str:
                return "b"

            @property
            def requires(self) -> list[type]:
                return [ModuleA]

            def configure(self, container: Container) -> None:
                pass

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass

        class ModuleC:
            @property
            def name(self) -> str:
                return "c"

            @property
            def requires(self) -> list[type]:
                return [ModuleA]

            def configure(self, container: Container) -> None:
                pass

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass

        class ModuleD:
            @property
            def name(self) -> str:
                return "d"

            @property
            def requires(self) -> list[type]:
                return [ModuleB, ModuleC]

            def configure(self, container: Container) -> None:
                pass

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass

        app = Application(auto_discover=False)
        app.add_module(as_module(ModuleD()))
        app.add_module(as_module(ModuleB()))
        app.add_module(as_module(ModuleC()))
        app.add_module(as_module(ModuleA()))

        app.initialize()

        names = [m.name for m in app._modules]
        # A must come before B, C, D
        assert names.index("a") < names.index("b")
        assert names.index("a") < names.index("c")
        assert names.index("a") < names.index("d")
        # B and C must come before D
        assert names.index("b") < names.index("d")
        assert names.index("c") < names.index("d")


# =============================================================================
# Module Lifecycle Tests
# =============================================================================


class TestModuleLifecycle:
    """Test module lifecycle phases."""

    def test_extend_phase_called_after_configure(self):
        """Test that extend is called after configure."""
        api_module = ApiModule()
        db_module = DatabaseModule()
        cache_module = CacheModule()

        app = Application(auto_discover=False)
        app.add_module(as_module(db_module))
        app.add_module(as_module(cache_module))
        app.add_module(as_module(api_module))

        assert not api_module.configured
        assert not api_module.extended

        app.initialize()

        assert api_module.configured
        assert api_module.extended

    def test_finalize_phase_called_after_compile(self):
        """Test that finalize is called after container compile."""
        api_module = ApiModule()
        db_module = DatabaseModule()
        cache_module = CacheModule()

        app = Application(auto_discover=False)
        app.add_module(as_module(db_module))
        app.add_module(as_module(cache_module))
        app.add_module(as_module(api_module))

        app.initialize()

        # Finalize should be called
        assert api_module.finalized

    @pytest.mark.asyncio
    async def test_start_and_stop_lifecycle(self):
        """Test module start and stop lifecycle."""
        db_module = DatabaseModule()

        app = Application(auto_discover=False)
        app.add_module(as_module(db_module))
        app.initialize()

        assert not db_module.started
        assert not db_module.stopped

        # Use lifespan
        lifespan = app.create_lifespan()
        async with lifespan(None):
            assert db_module.started
            assert not db_module.stopped

        assert db_module.stopped


# =============================================================================
# Module Query API Tests
# =============================================================================


class TestModuleQueryAPI:
    """Test module query APIs."""

    def test_get_module_by_type(self):
        """Test get_module returns correct module."""
        db_module = DatabaseModule()

        app = Application(auto_discover=False)
        app.add_module(as_module(db_module))
        app.initialize()

        result = app.get_module(DatabaseModule)
        assert result is db_module

    def test_get_module_not_found(self):
        """Test get_module raises for unknown module."""
        app = Application(auto_discover=False)
        app.add_module(as_module(DatabaseModule()))
        app.initialize()

        with pytest.raises(MyfyModuleNotFoundError):
            app.get_module(CacheModule)

    def test_has_module_returns_true(self):
        """Test has_module returns True for registered module."""
        app = Application(auto_discover=False)
        app.add_module(as_module(DatabaseModule()))
        app.initialize()

        assert app.has_module(DatabaseModule)

    def test_has_module_returns_false(self):
        """Test has_module returns False for unregistered module."""
        app = Application(auto_discover=False)
        app.add_module(as_module(DatabaseModule()))
        app.initialize()

        assert not app.has_module(CacheModule)

    def test_get_modules_implementing_protocol(self):
        """Test get_modules_implementing returns matching modules."""
        analytics_module = AnalyticsModule()
        db_module = DatabaseModule()

        app = Application(auto_discover=False)
        app.add_module(as_module(db_module))
        app.add_module(as_module(analytics_module))
        app.initialize()

        result = app.get_modules_implementing(AnalyticsProtocol)

        assert len(result) == 1
        assert result[0] is analytics_module

    def test_get_modules_implementing_empty(self):
        """Test get_modules_implementing returns empty list."""
        app = Application(auto_discover=False)
        app.add_module(as_module(DatabaseModule()))
        app.initialize()

        result = app.get_modules_implementing(AnalyticsProtocol)
        assert result == []


# =============================================================================
# Lifespan Tests
# =============================================================================


class TestApplicationLifespan:
    """Test application lifespan creation."""

    @pytest.mark.asyncio
    async def test_create_lifespan_returns_context_manager(self):
        """Test that create_lifespan returns working context manager."""
        app = Application(auto_discover=False)
        app.add_module(as_module(DatabaseModule()))
        app.initialize()

        lifespan = app.create_lifespan()

        async with lifespan(None):
            # Should be inside the context
            pass

    @pytest.mark.asyncio
    async def test_lifespan_starts_and_stops_modules(self):
        """Test that lifespan properly starts and stops modules."""
        db_module = DatabaseModule()

        app = Application(auto_discover=False)
        app.add_module(as_module(db_module))
        app.initialize()

        lifespan = app.create_lifespan()

        async with lifespan(None):
            assert db_module.started

        assert db_module.stopped

    @pytest.mark.asyncio
    async def test_lifespan_stops_on_exception(self):
        """Test that lifespan stops modules even on exception."""
        db_module = DatabaseModule()

        app = Application(auto_discover=False)
        app.add_module(as_module(db_module))
        app.initialize()

        lifespan = app.create_lifespan()

        with pytest.raises(ValueError):
            async with lifespan(None):
                assert db_module.started
                raise ValueError("Test error")

        # Module should still be stopped
        assert db_module.stopped
