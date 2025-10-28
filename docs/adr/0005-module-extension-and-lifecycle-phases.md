# ADR-0005: Module Extension Points and Lifecycle Phases

## Status

Proposed

## Context

The myfy framework is built on modularity (Principle #6: "Modular by design"), where modules like `WebModule`, `FrontendModule`, and `DataModule` provide independent functionality. However, the current single-phase initialization model creates architectural problems when modules need to extend or interact with each other.

### Current Lifecycle (Single Phase)

```python
# Application initialization flow (current)
app = Application()
app.add_module(WebModule())
app.add_module(FrontendModule())

# Inside Application.initialize():
for module in modules:
    module.configure(container)  # 1. Register services
container.compile()              # 2. Build services
# Later: start() called
```

### Problems with Current Model

**Problem 1: Extension Timing Mismatch**

When FrontendModule needs to extend WebModule's ASGI app (e.g., mount static files), there's no clean place to do it:
- **configure()** - Too early; ASGIApp not built yet, just registered
- **start()** - Too late; ASGIApp already created and may be in use (reload mode)

Current workaround in `frontend/module.py:171-209`:
```python
async def start(self):
    asgi_app = self._container.get(ASGIApp)
    asgi_app.app.mount(...)  # ❌ Mutates already-built service
```

This violates **Principle #5** ("Predictable lifecycle") because configuration happens in two phases.

**Problem 2: Implicit Dependencies**

Modules depend on each other, but dependencies are implicit and discovered via silent failure:

```python
try:
    asgi_app = self._container.get(ASGIApp)
except ProviderNotFoundError:
    logger.debug("WebModule not loaded, skipping...")  # Silent failure
    return
```

No way to declare: "FrontendModule requires WebModule"

**Problem 3: No Public Module Discovery API**

Code accesses private APIs to find modules:

```python
# In asgi_factory.py:72-81
for mod in application._modules:  # ❌ Private attribute
    if mod.name == "web":          # ❌ String matching
        web_module = mod
```

This violates **Principle #7** ("Replace anything") - can't swap WebModule implementations.

**Problem 4: No Type-Safe Extension Points**

Modules extend each other through duck typing and hope:
- FrontendModule assumes ASGIApp has `.app.mount()` method
- No formal contract for what WebModule provides
- No IDE support or type checking

### Real-World Impact

These issues surfaced in the frontend integration (ADR-0004):
1. Static file mounting happens in `start()` instead of configuration phase
2. Reload mode loses static mounts because ASGIApp is recreated
3. Module dependency on WebModule is implicit and fragile
4. Code duplication for lifespan creation across `main.py` and `asgi_factory.py`

## Decision

We will introduce **multi-phase initialization** with **explicit dependencies** and **type-safe extension protocols** to make module interactions predictable, type-safe, and replaceable.

### 1. Extended Module Protocol

Add optional lifecycle hooks to the Module protocol:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Module(Protocol):
    """Module protocol with extended lifecycle."""

    @property
    def name(self) -> str:
        """Unique module name (e.g., 'web', 'frontend')."""
        ...

    @property
    def requires(self) -> list[type]:
        """Module types this module depends on (default: [])."""
        return []

    @property
    def provides(self) -> list[type]:
        """Extension protocols this module implements (default: [])."""
        return []

    # PHASE 1: Register services in DI
    def configure(self, container: Container) -> None:
        """Register providers in the DI container."""
        ...

    # PHASE 2: Extend other modules (NEW)
    def extend(self, container: Container) -> None:
        """
        Extend other modules' services before they're finalized.

        Called after all modules have configured but before container compilation.
        Services are registered but not yet built (singletons not instantiated).

        Use this to:
        - Modify service registrations (e.g., wrap with middleware)
        - Add extension points to other modules' services
        - Register callbacks/hooks

        Default: no-op (most modules don't need this)
        """
        pass

    # PHASE 3: Finalize configuration (NEW)
    def finalize(self, container: Container) -> None:
        """
        Finalize module configuration after container compilation.

        Called after container is compiled and singletons can be resolved.
        Use this to:
        - Configure singleton services (e.g., mount static files on ASGIApp)
        - Register routes/middleware on web apps
        - Set up cross-module integrations

        Default: no-op (most modules don't need this)
        """
        pass

    # PHASE 4: Start runtime services
    async def start(self) -> None:
        """Start runtime services (databases, background tasks, etc.)."""
        ...

    # PHASE 5: Stop gracefully
    async def stop(self) -> None:
        """Stop and cleanup resources."""
        ...
```

### 2. Extension Protocol System

Define formal contracts for module extension:

```python
# myfy/web/extensions.py
from typing import Protocol
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.staticfiles import StaticFiles

class IWebExtension(Protocol):
    """Protocol for modules that extend WebModule."""

    def extend_asgi_app(self, app: Starlette) -> None:
        """
        Extend the ASGI application.

        Called during WebModule.finalize() to allow extensions to:
        - Mount static file directories
        - Add middleware
        - Register custom routes

        Args:
            app: The Starlette application instance
        """
        ...

class IMiddlewareProvider(Protocol):
    """Protocol for modules that provide middleware."""

    def get_middleware(self) -> list[Middleware]:
        """Return middleware to add to the ASGI app."""
        ...
```

### 3. Module Dependency Declaration

Modules explicitly declare dependencies:

```python
# FrontendModule example
class FrontendModule:
    @property
    def name(self) -> str:
        return "frontend"

    @property
    def requires(self) -> list[type]:
        """FrontendModule requires WebModule to be loaded."""
        return [WebModule]

    @property
    def provides(self) -> list[type]:
        """FrontendModule implements IWebExtension protocol."""
        return [IWebExtension]

    def configure(self, container: Container) -> None:
        """Register Jinja2Templates, AssetResolver, etc."""
        settings = load_settings(FrontendSettings)
        container.register(FrontendSettings, lambda: settings, scope="singleton")
        # ... other registrations

    def finalize(self, container: Container) -> None:
        """Mount static files on ASGI app (after it's built)."""
        # Get the ASGI app singleton (now built)
        asgi_app = container.get(ASGIApp)

        # Mount static files
        static_path = Path(self.static_dir) / "dist"
        if static_path.exists():
            asgi_app.app.mount("/static", StaticFiles(directory=str(static_path)))

    async def start(self) -> None:
        """Start Vite dev server (runtime service)."""
        await self._start_vite_dev_server()
```

### 4. Application Public API

Add public methods for module discovery:

```python
class Application:
    def get_module(self, module_type: type[T]) -> T:
        """
        Get a module by type.

        Args:
            module_type: The module class to find

        Returns:
            The module instance

        Raises:
            ModuleNotFoundError: If module not found
        """
        for module in self._modules:
            if isinstance(module, module_type):
                return module
        raise ModuleNotFoundError(f"Module {module_type.__name__} not found")

    def has_module(self, module_type: type) -> bool:
        """Check if a module type is registered."""
        return any(isinstance(m, module_type) for m in self._modules)

    def get_modules_implementing(self, protocol: type[T]) -> list[T]:
        """Get all modules implementing a specific protocol."""
        return [m for m in self._modules if protocol in getattr(m, 'provides', [])]

    def create_lifespan(self):
        """
        Create ASGI lifespan context manager.

        Returns a lifespan that starts/stops all modules.
        Centralizes lifespan creation for use in CLI and factories.
        """
        @asynccontextmanager
        async def lifespan(app):
            await self.lifecycle.start_all()
            try:
                yield
            finally:
                await self.lifecycle.stop_all()
        return lifespan
```

### 5. Multi-Phase Initialization Flow

Updated Application.initialize():

```python
def initialize(self) -> None:
    """
    Initialize application with multi-phase module setup.

    Phases:
    1. Discovery - Auto-discover modules via entry points
    2. Dependency Validation - Validate module dependency graph
    3. Configure - Modules register services in DI
    4. Extend - Modules modify service registrations (optional)
    5. Compile - DI container builds injection plans
    6. Finalize - Modules configure singleton services (optional)
    """
    if self._initialized:
        return

    # Phase 1: Discovery
    if self._auto_discover:
        self._discover_modules()

    # Phase 2: Validate dependencies
    self._validate_dependencies()

    # Phase 3: Configure (register services)
    self.container.register(CoreSettings, lambda: self.settings, scope="singleton")
    for module in self._modules:
        module.configure(self.container)
    register_providers_in_container(self.container)

    # Phase 4: Extend (optional, modify registrations)
    for module in self._modules:
        if hasattr(module, 'extend'):
            module.extend(self.container)

    # Phase 5: Compile DI container
    self.container.compile()

    # Phase 6: Finalize (configure singletons)
    for module in self._modules:
        if hasattr(module, 'finalize'):
            module.finalize(self.container)

    self._initialized = True

def _validate_dependencies(self) -> None:
    """
    Validate module dependency graph.

    Ensures:
    - All required modules are present
    - No circular dependencies
    - Modules are initialized in correct order
    """
    # Build dependency graph
    module_types = {type(m): m for m in self._modules}

    # Check all requirements are met
    for module in self._modules:
        for required_type in getattr(module, 'requires', []):
            if required_type not in module_types:
                raise ModuleDependencyError(
                    f"Module '{module.name}' requires {required_type.__name__} "
                    f"but it is not registered. Add it via app.add_module()."
                )

    # Check for circular dependencies
    visited = set()
    rec_stack = set()

    def has_cycle(module_type):
        visited.add(module_type)
        rec_stack.add(module_type)

        module = module_types[module_type]
        for required_type in getattr(module, 'requires', []):
            if required_type not in visited:
                if has_cycle(required_type):
                    return True
            elif required_type in rec_stack:
                return True

        rec_stack.remove(module_type)
        return False

    for module_type in module_types:
        if module_type not in visited:
            if has_cycle(module_type):
                raise ModuleDependencyError("Circular module dependency detected")

    # Sort modules by dependency order (topological sort)
    self._modules = self._topological_sort_modules()
```

### 6. Updated WebModule Integration

WebModule provides extension points:

```python
class WebModule:
    @property
    def provides(self) -> list[type]:
        return [IMiddlewareProvider]  # Implements middleware protocol

    def configure(self, container: Container) -> None:
        """Register Router, ASGIApp factory, etc."""
        # ... existing registration code

        # Register ASGIApp factory (without lifespan yet)
        def create_asgi_app(router: Router) -> ASGIApp:
            return ASGIApp(container, router)

        container.register(ASGIApp, create_asgi_app, scope="singleton")

    def finalize(self, container: Container) -> None:
        """
        Finalize ASGI app by collecting extensions.

        This is where IWebExtension modules can extend the app.
        """
        # At this point, ASGIApp singleton is built
        # Extensions can now modify it
        pass  # Extensions handle themselves in their finalize()

    def get_asgi_app(self, container: Container, lifespan=None) -> ASGIApp:
        """Get ASGI app (optionally with lifespan)."""
        if lifespan:
            # Create new instance with lifespan (for CLI)
            router = container.get(Router)
            return ASGIApp(container, router, lifespan=lifespan)
        else:
            # Get singleton from DI
            return container.get(ASGIApp)
```

### 7. Example: FrontendModule Using New Architecture

```python
class FrontendModule:
    @property
    def requires(self) -> list[type]:
        return [WebModule]  # Explicit dependency

    @property
    def provides(self) -> list[type]:
        return [IWebExtension]  # Implements extension protocol

    def configure(self, container: Container) -> None:
        """Register templates, assets, etc."""
        settings = load_settings(FrontendSettings)
        container.register(FrontendSettings, lambda: settings, scope="singleton")

        asset_resolver = AssetResolver(static_dir=self.static_dir, settings=settings)
        container.register(AssetResolver, lambda: asset_resolver, scope="singleton")

        templates = create_templates_instance(...)
        container.register(Jinja2Templates, lambda: templates, scope="singleton")

    def finalize(self, container: Container) -> None:
        """
        Mount static files on ASGI app.

        Called after container is compiled, so ASGIApp singleton is built.
        This is the RIGHT place to extend the ASGI app.
        """
        asgi_app = container.get(ASGIApp)
        settings = container.get(FrontendSettings)

        static_path = Path(self.static_dir) / "dist"
        if static_path.exists():
            asgi_app.app.mount(
                settings.static_url_prefix,
                StaticFiles(directory=str(static_path)),
                name="static"
            )
            logger.info(f"✅ Static files mounted at {settings.static_url_prefix}")

    async def start(self) -> None:
        """Start Vite dev server (runtime service)."""
        settings = self._container.get(FrontendSettings)
        if settings.environment == "development":
            await self._start_vite_dev_server()
```

### 8. CLI Integration Simplified

```python
# myfy_cli/asgi_factory.py
def create_app(app_module: str | None = None, app_var: str | None = None):
    """Factory for uvicorn --factory mode."""
    # ... import application

    application = getattr(module, app_var)
    if not application._initialized:
        application.initialize()

    # Use public API instead of private access
    web_module = application.get_module(WebModule)

    # Use centralized lifespan creation
    lifespan = application.create_lifespan()

    # Get ASGI app with lifespan
    asgi_app = web_module.get_asgi_app(application.container, lifespan=lifespan)
    return asgi_app.app
```

## Consequences

### Positive

1. **Predictable Lifecycle** (Principle #5)
   - Clear phases: configure → extend → compile → finalize → start
   - No service mutation after creation
   - Configuration complete before runtime

2. **Type-Safe Extensions** (Principle #8)
   - Extension protocols are typed and checkable
   - IDE autocomplete for extension methods
   - Runtime validation of protocol implementation

3. **Explicit Dependencies** (Principle #6)
   - Dependencies declared, not discovered
   - Fail-fast on missing dependencies
   - Clear module initialization order

4. **Replace Anything** (Principle #7)
   - Public APIs for module discovery
   - No hardcoded string matching
   - Modules can be swapped without breaking code

5. **Backward Compatible**
   - `extend()` and `finalize()` are optional
   - Existing modules work without changes
   - Gradual migration path

6. **Better Developer Experience** (Principle #16-17)
   - Clear error messages for missing dependencies
   - Type hints guide extension development
   - No hidden magic or private API access

7. **Testability** (Principle #19)
   - Easy to mock module dependencies
   - Can test modules in isolation
   - Dependency graph is inspectable

### Neutral

1. **More Lifecycle Hooks**
   - Developers need to understand when to use each phase
   - Documentation burden to explain configure vs extend vs finalize
   - More methods in Module protocol (but all optional)

2. **Dependency Declaration Overhead**
   - Modules must explicitly declare dependencies
   - Adds a few lines of boilerplate per module

### Negative

1. **Migration Required for Existing Modules**
   - FrontendModule needs refactoring to use finalize()
   - WebModule needs minor updates
   - Documentation needs updating

2. **Slightly More Complex Initialization**
   - Six phases instead of three
   - More state transitions to reason about
   - Potential for confusion about which phase to use

3. **Protocol Proliferation Risk**
   - Need discipline to avoid creating too many protocols
   - Risk of over-engineering extension points
   - Maintenance burden for protocol definitions

## Alternatives Considered

### 1. Single-Phase with Lazy Initialization

Keep single `configure()` but make all service creation lazy:

```python
def configure(self, container):
    # Register lazy factory
    def create_asgi_app():
        app = ASGIApp(...)
        # Collect extensions here lazily
        for ext in get_extensions():
            ext.extend(app)
        return app
    container.register(ASGIApp, create_asgi_app)
```

**Rejected because:**
- Order of extension is unpredictable
- Extensions happen on first access, not during initialization
- Violates Principle #5 (Predictable lifecycle)
- Hard to reason about when extensions run

### 2. Event/Callback System

Use pub-sub pattern for module communication:

```python
# Modules subscribe to events
@on_event("asgi_app_created")
def mount_static_files(asgi_app):
    asgi_app.mount(...)

# WebModule emits events
events.emit("asgi_app_created", asgi_app)
```

**Rejected because:**
- Order of callbacks is implicit
- Not type-safe (string event names)
- Hard to discover what events exist
- Debugging is difficult (who subscribed?)
- Violates Principle #4 (Pythonic over ceremonial)

### 3. Dependency Injection Only (No Extension Points)

Rely purely on DI for module interaction:

```python
class FrontendModule:
    def configure(self, container):
        # Register a "static mounts" service
        container.register(StaticMounts, lambda: [...])

class WebModule:
    def configure(self, container):
        # Consume all StaticMounts
        mounts = container.get_all(StaticMounts)
        # But when to mount them? Problem remains...
```

**Rejected because:**
- Doesn't solve timing problem (when to mount?)
- Forces all extensions into DI (not everything fits)
- Loss of explicit module relationships
- Harder to understand data flow

### 4. Post-Compile Hook Only (No Finalize)

Add single `post_compile()` hook instead of full phase system:

```python
class Module(Protocol):
    def configure(self, container): ...
    def post_compile(self, container): ...  # Called after compile
    async def start(self): ...
```

**Rejected because:**
- Doesn't provide extension point before compilation
- Can't modify service registrations (already compiled)
- Less flexible than multi-phase approach
- Missed opportunity to improve architecture

### 5. Modules Return Configuration Objects

Modules return configuration, framework assembles:

```python
class FrontendModule:
    def get_config(self) -> ModuleConfig:
        return ModuleConfig(
            dependencies=[WebModule],
            services={...},
            extensions={...}
        )

# Framework assembles
for module in modules:
    config = module.get_config()
    # Process config
```

**Rejected because:**
- Too declarative, loses imperative power
- Hard to handle complex configuration logic
- Doesn't align with Principle #4 (Pythonic)
- Forces all configuration into data structures

### 6. Separate Extension Modules

Create separate extension modules instead of protocols:

```python
app.add_module(WebModule())
app.add_module(FrontendModule())
app.add_module(FrontendWebExtension())  # Separate module for extension
```

**Rejected because:**
- Artificial module proliferation
- More complex for users (3 modules instead of 2)
- Violates Principle #2 (Defaults by default)
- Worse developer experience

## Migration Path

### Phase 1: Add New APIs (Backward Compatible)

1. Add `extend()` and `finalize()` to Module protocol as optional methods
2. Add `requires` and `provides` properties with defaults
3. Add public APIs to Application: `get_module()`, `has_module()`, `create_lifespan()`
4. Update `Application.initialize()` to call new phases if methods exist
5. Define `IWebExtension` protocol in myfy-web

**Result:** All existing code works, new features available.

### Phase 2: Migrate FrontendModule

1. Move static mounting from `start()` to `finalize()`
2. Add `requires = [WebModule]` declaration
3. Add `provides = [IWebExtension]` declaration
4. Update documentation

**Result:** FrontendModule uses new architecture, no breaking changes.

### Phase 3: Migrate CLI

1. Use `application.get_module(WebModule)` instead of private access
2. Use `application.create_lifespan()` instead of inline creation
3. Remove code duplication between `main.py` and `asgi_factory.py`

**Result:** Cleaner CLI code using public APIs.

### Phase 4: Documentation and Examples

1. Update module development guide
2. Document lifecycle phases
3. Create examples of extension protocols
4. Add migration guide for existing modules

**Result:** Developers understand new patterns.

## Implementation Checklist

- [ ] Define `IWebExtension` and other extension protocols
- [ ] Add `extend()` and `finalize()` to Module protocol
- [ ] Add `requires` and `provides` properties to Module protocol
- [ ] Implement `_validate_dependencies()` in Application
- [ ] Implement `_topological_sort_modules()` in Application
- [ ] Add public APIs: `get_module()`, `has_module()`, `get_modules_implementing()`
- [ ] Add `create_lifespan()` to Application
- [ ] Update `Application.initialize()` to support multi-phase
- [ ] Migrate FrontendModule to use `finalize()`
- [ ] Update CLI to use public APIs
- [ ] Write tests for dependency validation
- [ ] Write tests for lifecycle phases
- [ ] Update documentation
- [ ] Create migration guide

## References

- [PRINCIPLES.md](../../PRINCIPLES.md) - Framework design philosophy
- [ADR-0002](./0002-modular-configuration-design.md) - Modular configuration
- [ADR-0003](./0003-dependency-injection-with-scopes.md) - DI with scopes
- [ADR-0004](./0004-frontend-module-integration.md) - Frontend module integration
- [Module Protocol](../../packages/myfy-core/myfy/core/kernel/module.py) - Current module implementation
- [Application Kernel](../../packages/myfy-core/myfy/core/kernel/app.py) - Current application implementation
- [ASP.NET Core Startup](https://docs.microsoft.com/en-us/aspnet/core/fundamentals/startup) - Similar multi-phase pattern
- [NestJS Module System](https://docs.nestjs.com/modules) - Explicit dependencies inspiration
