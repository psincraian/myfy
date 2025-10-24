"""
Application kernel - the heart of myfy.

Coordinates DI, modules, configuration, and lifecycle.
"""

from typing import List, Type, Optional, Any
import asyncio
from importlib.metadata import entry_points

from ..di import Container, register_providers_in_container
from ..config import BaseSettings, CoreSettings, load_settings
from .module import Module
from .lifecycle import LifecycleManager


class Application:
    """
    The myfy application kernel.

    Lifecycle:
    1. Create application instance
    2. Configure modules and providers
    3. Initialize (compile DI, discover modules)
    4. Start modules
    5. Run
    6. Stop modules gracefully

    Usage:
        app = Application()
        app.add_module(WebModule())
        await app.run()
    """

    def __init__(
        self,
        settings_class: Type[BaseSettings] = CoreSettings,
        auto_discover: bool = True,
    ):
        """
        Create a new application.

        Args:
            settings_class: Settings class to load
            auto_discover: Automatically discover modules via entry points
        """
        self.container = Container()
        self.settings = load_settings(settings_class)

        # Get shutdown timeout from settings or use default
        shutdown_timeout = getattr(self.settings, "shutdown_timeout", 10.0)
        self.lifecycle = LifecycleManager(timeout=shutdown_timeout)

        self._initialized = False
        self._modules: List[Module] = []
        self._auto_discover = auto_discover

    def add_module(self, module: Module) -> None:
        """
        Register a module with the application.

        Must be called before initialize().

        Args:
            module: The module to add
        """
        if self._initialized:
            raise RuntimeError(
                "Cannot add modules after initialization. "
                "Add modules before calling initialize() or run()."
            )
        self._modules.append(module)
        self.lifecycle.add_module(module)

    def initialize(self) -> None:
        """
        Initialize the application.

        Steps:
        1. Discover modules via entry points (if auto_discover enabled)
        2. Register settings in container
        3. Configure all modules (register providers)
        4. Register @provider decorated functions
        5. Compile DI container

        This must be called before start() or run().
        """
        if self._initialized:
            return

        # Auto-discover modules via entry points
        if self._auto_discover:
            self._discover_modules()

        # Register core settings as singleton
        self.container.register(
            type_=type(self.settings),
            factory=lambda: self.settings,
            scope="singleton",
        )

        # Also make CoreSettings available if using a custom settings class
        if not isinstance(self.settings, CoreSettings):
            self.container.register(
                type_=CoreSettings,
                factory=lambda: self.settings,  # type: ignore
                scope="singleton",
            )

        # Configure all modules (let them register providers)
        for module in self._modules:
            module.configure(self.container)

        # Register any @provider decorated functions
        register_providers_in_container(self.container)

        # Compile the container (build injection plans, detect cycles)
        self.container.compile()

        self._initialized = True

    def _discover_modules(self) -> None:
        """
        Discover and load modules via entry points.

        Looks for entry points in the 'myfy.modules' group.
        """
        try:
            discovered = entry_points(group="myfy.modules")
            for ep in discovered:
                try:
                    module_factory = ep.load()
                    # Entry point should be a Module instance or a callable that returns one
                    if callable(module_factory):
                        module = module_factory()
                    else:
                        module = module_factory

                    if isinstance(module, Module):
                        self.add_module(module)
                except Exception as e:
                    print(
                        f"Warning: Failed to load module '{ep.name}' from {ep.value}: {e}"
                    )
        except Exception as e:
            # Entry points discovery failed - not critical
            print(f"Warning: Module discovery failed: {e}")

    async def start(self) -> None:
        """
        Start the application.

        Initializes (if not already done) and starts all modules.
        """
        if not self._initialized:
            self.initialize()

        await self.lifecycle.start_all()

    async def stop(self) -> None:
        """Stop the application gracefully."""
        await self.lifecycle.stop_all()

    async def run(self) -> None:
        """
        Run the application until shutdown signal.

        This is the main entry point for running the application.
        Sets up signal handlers and manages the full lifecycle.

        Usage:
            app = Application()
            await app.run()
        """
        if not self._initialized:
            self.initialize()

        # Set up signal handlers for graceful shutdown
        self.lifecycle.setup_signal_handlers()

        async with self.lifecycle.lifespan():
            print(f"🚀 {self.settings.app_name} started")
            print(f"📦 Loaded {len(self._modules)} module(s): {', '.join(m.name for m in self._modules)}")

            # Wait for shutdown signal
            await self.lifecycle.wait_for_shutdown()

        print(f"👋 {self.settings.app_name} stopped")

    def __repr__(self) -> str:
        return (
            f"Application(modules={len(self._modules)}, "
            f"initialized={self._initialized})"
        )
