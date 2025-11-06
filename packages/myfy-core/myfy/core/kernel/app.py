"""
Application kernel - the heart of myfy.

Coordinates DI, modules, configuration, and lifecycle.
"""

from contextlib import asynccontextmanager
from importlib.metadata import entry_points
from typing import TypeVar

from ..config import BaseSettings, CoreSettings, load_settings
from ..di import SINGLETON, Container, register_providers_in_container
from .errors import ModuleDependencyError, MyfyModuleNotFoundError
from .lifecycle import LifecycleManager
from .module import Module

T = TypeVar("T")
ModuleType = TypeVar("ModuleType", bound=Module)


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
        settings_class: type[BaseSettings] = CoreSettings,
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
        self._modules: list[Module] = []
        self._auto_discover = auto_discover

    def add_module[T: ModuleType](self, module: type[T]) -> None:
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

    def get_module(self, module_type: type[T]) -> T:
        """
        Get a module by type.

        Args:
            module_type: The module class to find (e.g., WebModule)

        Returns:
            The module instance

        Raises:
            ModuleNotFoundError: If module not found

        Example:
            web_module = app.get_module(WebModule)
        """
        for module in self._modules:
            if isinstance(module, module_type):
                return module  # type: ignore
        raise MyfyModuleNotFoundError(module_type)

    def has_module(self, module_type: type) -> bool:
        """
        Check if a module type is registered.

        Args:
            module_type: The module class to check

        Returns:
            True if module is registered, False otherwise

        Example:
            if app.has_module(FrontendModule):
                print("Frontend module is loaded")
        """
        return any(isinstance(m, module_type) for m in self._modules)

    def get_modules_implementing(self, protocol: type[T]) -> list[T]:
        """
        Get all modules implementing a specific protocol.

        Args:
            protocol: The protocol type to filter by (e.g., IWebExtension)

        Returns:
            List of modules that declare they implement the protocol

        Example:
            extensions = app.get_modules_implementing(IWebExtension)
            for ext in extensions:
                ext.extend_asgi_app(asgi_app)
        """
        result = []
        for module in self._modules:
            provides = getattr(module, "provides", [])
            if protocol in provides:
                result.append(module)  # type: ignore
        return result

    def create_lifespan(self):
        """
        Create lifespan context manager.

        Returns a lifespan context that starts/stops all modules.
        This centralizes lifespan creation for use in CLI and factories.

        Returns:
            lifespan context manager

        Example:
            lifespan = app.create_lifespan()
            asgi_app = web_module.get_asgi_app(container, lifespan=lifespan)
        """

        @asynccontextmanager
        async def lifespan(app):  # noqa: ARG001
            """lifespan that manages all module lifecycles."""
            await self.lifecycle.start_all()
            try:
                yield
            finally:
                await self.lifecycle.stop_all()

        return lifespan

    def initialize(self) -> None:
        """
        Initialize the application with multi-phase module setup.

        Phases:
        1. Discovery - Auto-discover modules via entry points
        2. Dependency Validation - Validate module dependency graph
        3. Configure - Modules register services in DI
        4. Extend - Modules modify service registrations (optional)
        5. Compile - DI container builds injection plans
        6. Finalize - Modules configure singleton services (optional)

        This must be called before start() or run().
        """
        if self._initialized:
            return

        # Phase 1: Discovery
        if self._auto_discover:
            self._discover_modules()

        # Phase 2: Validate dependencies (fail-fast)
        self._validate_dependencies()

        # Register core settings as singleton
        self.container.register(
            type_=type(self.settings),
            factory=lambda: self.settings,
            scope=SINGLETON,
        )

        # Also make CoreSettings available if using a custom settings class
        if not isinstance(self.settings, CoreSettings):
            self.container.register(
                type_=CoreSettings,
                factory=lambda: self.settings,  # type: ignore
                scope=SINGLETON,
            )

        # Register nested module settings (ADR-0007: Optional Nested Module Settings)
        # If user's settings class contains nested BaseSettings, register them too
        self._register_nested_settings()

        # Phase 3: Configure (register services)
        for module in self._modules:
            module.configure(self.container)

        # Register any @provider decorated functions
        register_providers_in_container(self.container)

        # Phase 4: Extend (optional - modify registrations)
        for module in self._modules:
            if hasattr(module, "extend"):
                module.extend(self.container)

        # Phase 5: Compile the container (build injection plans, detect cycles)
        self.container.compile()

        # Phase 6: Finalize (optional - configure singletons)
        for module in self._modules:
            if hasattr(module, "finalize"):
                module.finalize(self.container)

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
                    module = module_factory() if callable(module_factory) else module_factory

                    if isinstance(module, Module):
                        self.add_module(module)
                except Exception as e:
                    print(f"Warning: Failed to load module '{ep.name}' from {ep.value}: {e}")
        except Exception as e:
            # Entry points discovery failed - not critical
            print(f"Warning: Module discovery failed: {e}")

    def _register_nested_settings(self) -> None:
        """
        Register nested module settings found in user's settings class.

        Supports ADR-0007: Optional Nested Module Settings pattern.
        Allows users to define module settings as nested Pydantic models:

        Example:
            class AppSettings(BaseSettings):
                app_name: str = "My App"
                web: WebSettings = Field(default_factory=WebSettings)

        The nested settings are already loaded with environment variables
        (using their module prefixes like MYFY_WEB_*) when Pydantic loaded
        the parent settings. We just need to register them in the container.
        """

        # Iterate over all fields in the settings class
        for field_name in dir(self.settings):
            # Skip private/magic attributes
            if field_name.startswith("_"):
                continue

            try:
                field_value = getattr(self.settings, field_name)

                # Check if this field is a BaseSettings instance
                if isinstance(field_value, BaseSettings):
                    # Get the class of this nested settings
                    settings_class = type(field_value)

                    # Create a proper factory closure
                    # This avoids default argument issues with container DI inspection
                    def make_factory(val):
                        def factory():
                            return val

                        return factory

                    # Register this nested settings as a singleton
                    # Using the nested instance directly (already has env vars loaded)
                    self.container.register(
                        type_=settings_class,
                        factory=make_factory(field_value),
                        scope=SINGLETON,
                    )

                    # If this is a subclass (e.g., from override()), also register it
                    # under its base class so DI can find it
                    # This allows override() to work with dependency injection
                    for base in settings_class.__bases__:
                        if base is not BaseSettings and issubclass(base, BaseSettings):
                            # Register under the base class as well (e.g., WebSettings)
                            self.container.register(
                                type_=base,
                                factory=make_factory(field_value),
                                scope=SINGLETON,
                            )
            except Exception:
                # Skip fields that can't be accessed or cause errors
                continue

    def _validate_dependencies(self) -> None:
        """
        Validate module dependency graph.

        Ensures:
        - All required modules are present
        - No circular dependencies
        - Returns modules in dependency order (topological sort)

        Raises:
            ModuleDependencyError: If dependencies cannot be satisfied
        """
        # Build module type map
        module_types = {type(m): m for m in self._modules}

        # Check all requirements are met
        for module in self._modules:
            requires = getattr(module, "requires", [])
            for required_type in requires:
                if required_type not in module_types:
                    raise ModuleDependencyError(
                        f"Module '{module.name}' ({type(module).__name__}) requires "
                        f"{required_type.__name__} but it is not registered. "
                        f"Add it via app.add_module({required_type.__name__}())."
                    )

        # Check for circular dependencies using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(module_type):
            visited.add(module_type)
            rec_stack.add(module_type)

            module = module_types[module_type]
            requires = getattr(module, "requires", [])

            for required_type in requires:
                if required_type not in visited:
                    if has_cycle(required_type):
                        return True
                elif required_type in rec_stack:
                    # Found a cycle
                    return True

            rec_stack.remove(module_type)
            return False

        for module_type in module_types:
            if module_type not in visited and has_cycle(module_type):
                raise ModuleDependencyError(
                    "Circular module dependency detected. "
                    "Check your module 'requires' declarations."
                )

        # Sort modules by dependency order (topological sort)
        self._modules = self._topological_sort_modules()

    def _topological_sort_modules(self) -> list[Module]:
        """
        Sort modules in dependency order using topological sort.

        Returns:
            List of modules in dependency order (dependencies first)
        """
        # Build adjacency list and in-degree map
        module_map = {type(m): m for m in self._modules}
        in_degree = {type(m): 0 for m in self._modules}
        adj_list = {type(m): [] for m in self._modules}

        # Build graph
        for module in self._modules:
            module_type = type(module)
            requires = getattr(module, "requires", [])
            for required_type in requires:
                # required_type -> module_type (dependency edge)
                adj_list[required_type].append(module_type)
                in_degree[module_type] += 1

        # Kahn's algorithm for topological sort
        queue = [mt for mt in in_degree if in_degree[mt] == 0]
        sorted_types = []

        while queue:
            current_type = queue.pop(0)
            sorted_types.append(current_type)

            for dependent_type in adj_list[current_type]:
                in_degree[dependent_type] -= 1
                if in_degree[dependent_type] == 0:
                    queue.append(dependent_type)

        # Convert types back to module instances
        return [module_map[mt] for mt in sorted_types]

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
            app_name = getattr(self.settings, "app_name", "myfy-app")
            print(f"🚀 {app_name} started")
            print(
                f"📦 Loaded {len(self._modules)} module(s): {', '.join(m.name for m in self._modules)}"
            )

            # Wait for shutdown signal
            await self.lifecycle.wait_for_shutdown()

        print(f"👋 {app_name} stopped")

    def __repr__(self) -> str:
        return f"Application(modules={len(self._modules)}, initialized={self._initialized})"
