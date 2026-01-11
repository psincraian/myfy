---
name: scaffold-module
description: Scaffold a new myfy module following the Module protocol
---

# Module Scaffolding Agent

You are an expert at creating myfy modules. Guide the user through creating a new module.

## Process

1. **Gather Requirements**
   - Module name (e.g., "notifications", "caching", "analytics")
   - Module dependencies (WebModule, DataModule, etc.)
   - Services it should provide
   - Whether it needs settings

2. **Generate Files**

### Module File (`{module_name}/module.py`)

```python
"""
{ModuleName} module for myfy.

{Description}
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from myfy.core import BaseModule, SINGLETON
from myfy.core.config import load_settings
from myfy.core.di.types import ProviderKey

from .config import {ModuleName}Settings
from .service import {ModuleName}Service

if TYPE_CHECKING:
    from myfy.core.di import Container

logger = logging.getLogger(__name__)


class {ModuleName}Module(BaseModule):
    """
    {ModuleName} module.

    Features:
    - {Feature 1}
    - {Feature 2}
    """

    def __init__(
        self,
        settings: {ModuleName}Settings | None = None,
    ) -> None:
        super().__init__("{module-name}")
        self._settings = settings

    @property
    def requires(self) -> list[type]:
        return [{RequiredModules}]

    @property
    def provides(self) -> list[type]:
        return []

    def configure(self, container: Container) -> None:
        """Register services in DI container."""
        logger.debug(f"Configuring {ModuleName}Module...")

        # Register settings
        key = ProviderKey({ModuleName}Settings)
        if key not in container._providers:
            if self._settings is None:
                self._settings = load_settings({ModuleName}Settings)
            container.register(
                type_={ModuleName}Settings,
                factory=lambda: self._settings,
                scope=SINGLETON,
            )

        # Register services
        container.register(
            type_={ModuleName}Service,
            factory=lambda settings=self._settings: {ModuleName}Service(settings),
            scope=SINGLETON,
        )

        logger.debug(f"{ModuleName}Module configured")

    async def start(self) -> None:
        """Start runtime services."""
        logger.info("{ModuleName} module started")

    async def stop(self) -> None:
        """Stop and cleanup."""
        logger.info("{ModuleName} module stopped")

    def __repr__(self) -> str:
        return f"{ModuleName}Module()"


# Module instance for entry point
{module_name}_module = {ModuleName}Module()
```

### Settings File (`{module_name}/config.py`)

```python
"""Settings for {ModuleName} module."""
from pydantic import Field
from pydantic_settings import SettingsConfigDict

from myfy.core import BaseSettings


class {ModuleName}Settings(BaseSettings):
    """{ModuleName} configuration."""

    enabled: bool = Field(default=True, description="Enable {module_name}")
    # Add your settings here

    model_config = SettingsConfigDict(
        env_prefix="MYFY_{MODULE_NAME}_",
        env_file=".env",
    )
```

### Service File (`{module_name}/service.py`)

```python
"""Service for {ModuleName} module."""
from .config import {ModuleName}Settings


class {ModuleName}Service:
    """{ModuleName} service."""

    def __init__(self, settings: {ModuleName}Settings) -> None:
        self._settings = settings

    # Add your methods here
```

### Init File (`{module_name}/__init__.py`)

```python
"""{ModuleName} module for myfy."""
from .config import {ModuleName}Settings
from .module import {ModuleName}Module, {module_name}_module
from .service import {ModuleName}Service

__all__ = [
    "{ModuleName}Module",
    "{ModuleName}Service",
    "{ModuleName}Settings",
    "{module_name}_module",
]
```

3. **Provide Usage Example**

```python
from myfy.core import Application
from {module_name} import {ModuleName}Module

app = Application()
app.add_module({ModuleName}Module())
```

## Naming Conventions

- Module class: `{ModuleName}Module` (PascalCase + "Module")
- Settings class: `{ModuleName}Settings` (PascalCase + "Settings")
- Module instance: `{module_name}_module` (snake_case + "_module")
- Package name: `{module_name}` (snake_case)
- Env prefix: `MYFY_{MODULE_NAME}_` (uppercase with underscore)

## Guidelines

- Always use type hints
- Include logging for debugging
- Support settings injection for testing
- Check for existing registrations to avoid duplicates
- Make start/stop idempotent
