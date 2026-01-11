---
name: module-development
description: myfy module protocol, lifecycle phases, and extension patterns. Use when creating new modules, working with configure/extend/finalize methods, or module dependencies.
---

# Module Development in myfy

Modules are the building blocks of myfy applications. Each module follows a protocol with lifecycle hooks.

## Module Protocol

```python
from myfy.core import BaseModule, Container, SINGLETON

class MyModule(BaseModule):
    """Custom module following the Module protocol."""

    def __init__(self):
        super().__init__(name="my-module")

    @property
    def requires(self) -> list[type]:
        """Module types this module depends on."""
        return []  # e.g., [WebModule, DataModule]

    @property
    def provides(self) -> list[type]:
        """Extension protocols this module implements."""
        return []  # e.g., [IWebExtension]

    def configure(self, container: Container) -> None:
        """Phase 1: Register providers in DI container."""
        container.register(
            type_=MyService,
            factory=lambda: MyService(),
            scope=SINGLETON,
        )

    def extend(self, container: Container) -> None:
        """Phase 2: Modify other modules' registrations (optional)."""
        pass

    def finalize(self, container: Container) -> None:
        """Phase 3: Configure singletons after compilation (optional)."""
        # Safe to get singletons here - container is compiled
        service = container.get(MyService)
        service.setup()

    async def start(self) -> None:
        """Phase 4: Start runtime services (connect to DB, etc.)."""
        pass

    async def stop(self) -> None:
        """Phase 5: Cleanup resources gracefully."""
        pass
```

## Lifecycle Phases

1. **Discovery** - Application discovers all modules
2. **Dependency Validation** - Validates module dependency graph
3. **Configure** - Each module registers services in DI
4. **Extend** - Modules can modify other modules' registrations
5. **Compile** - DI container builds injection plans
6. **Finalize** - Modules configure singleton services
7. **Start** - Runtime services start (in dependency order)
8. **Stop** - Graceful shutdown (reverse order)

## Module Dependencies

Declare dependencies via the `requires` property:

```python
from myfy.web import WebModule
from myfy.data import DataModule

class MyModule(BaseModule):
    @property
    def requires(self) -> list[type]:
        # This module needs WebModule and DataModule to be registered
        return [WebModule, DataModule]
```

The application validates all required modules are present and initializes them in topological order.

## Registering Settings

Modules typically register their own settings:

```python
from myfy.core.config import load_settings
from myfy.core.di.types import ProviderKey

class MyModule(BaseModule):
    def __init__(self, settings: MySettings | None = None):
        super().__init__("my-module")
        self._settings = settings

    def configure(self, container: Container) -> None:
        # Check if settings already registered (avoid double registration)
        key = ProviderKey(MySettings)
        if key not in container._providers:
            if self._settings is None:
                self._settings = load_settings(MySettings)
            container.register(
                type_=MySettings,
                factory=lambda: self._settings,
                scope=SINGLETON,
            )
```

## Extension Protocols

Define extension interfaces using `provides`:

```python
from myfy.web.extensions import IWebExtension

class MyModule(BaseModule):
    @property
    def provides(self) -> list[type]:
        return [IWebExtension]

    def finalize(self, container: Container) -> None:
        # Access ASGIApp after compilation
        asgi_app = container.get(ASGIApp)
        asgi_app.app.mount("/my-path", MyASGIApp())
```

## Complete Module Example

```python
"""
MyFeature module for myfy.

Provides feature X with Y capabilities.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from myfy.core import BaseModule, SINGLETON
from myfy.core.config import load_settings
from myfy.core.di.types import ProviderKey

from .config import MyFeatureSettings
from .service import MyFeatureService

if TYPE_CHECKING:
    from myfy.core.di import Container

logger = logging.getLogger(__name__)


class MyFeatureModule(BaseModule):
    """
    MyFeature module.

    Features:
    - Feature capability 1
    - Feature capability 2
    """

    def __init__(self, settings: MyFeatureSettings | None = None):
        super().__init__("my-feature")
        self._settings = settings

    @property
    def requires(self) -> list[type]:
        return []

    @property
    def provides(self) -> list[type]:
        return []

    def configure(self, container: Container) -> None:
        logger.debug("Configuring MyFeatureModule...")

        # Register settings
        key = ProviderKey(MyFeatureSettings)
        if key not in container._providers:
            if self._settings is None:
                self._settings = load_settings(MyFeatureSettings)
            container.register(
                type_=MyFeatureSettings,
                factory=lambda: self._settings,
                scope=SINGLETON,
            )

        # Register services
        container.register(
            type_=MyFeatureService,
            factory=lambda settings=self._settings: MyFeatureService(settings),
            scope=SINGLETON,
        )

        logger.debug("MyFeatureModule configured")

    async def start(self) -> None:
        logger.info("MyFeature module started")

    async def stop(self) -> None:
        logger.info("MyFeature module stopped")


# Module instance for entry point discovery
my_feature_module = MyFeatureModule()
```

## Best Practices

1. **Always call super().__init__(name)** - Required by BaseModule
2. **Use logging** - Add debug/info logs for troubleshooting
3. **Allow settings injection** - Accept optional settings in __init__ for testing
4. **Check for existing registrations** - Avoid double registration errors
5. **Keep configure() pure** - Only register providers, no side effects
6. **Use finalize() for singletons** - Safe to resolve singletons here
7. **Make start/stop idempotent** - Safe to call multiple times
8. **Include docstrings** - Document what the module provides
