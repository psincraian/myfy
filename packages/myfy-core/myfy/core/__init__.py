"""
myfy-core: The kernel of the myfy framework.

Provides:
- Dependency injection with compile-time resolution
- Configuration with profiles
- Application kernel and module system
- Lifecycle management

Usage:
    from myfy.core import Application, provider, SINGLETON
    from myfy.core.config import BaseSettings

    class Settings(BaseSettings):
        db_url: str

    @provider(scope=SINGLETON)
    def database(settings: Settings) -> Database:
        return Database(settings.db_url)

    app = Application(settings_class=Settings)
    await app.run()
"""

from .kernel import Application, Module, BaseModule
from .di import (
    Container,
    provider,
    SINGLETON,
    REQUEST,
    TASK,
    Qualifier,
    ScopeContext,
)
from .config import BaseSettings, CoreSettings, Profile, load_settings

__all__ = [
    # Kernel
    "Application",
    "Module",
    "BaseModule",
    # DI
    "Container",
    "provider",
    "SINGLETON",
    "REQUEST",
    "TASK",
    "Qualifier",
    "ScopeContext",
    # Config
    "BaseSettings",
    "CoreSettings",
    "Profile",
    "load_settings",
]

# Module instance for entry point
from .kernel import BaseModule as _BaseModule


class _CoreModule(_BaseModule):
    """Core module (minimal - just provides core services)."""

    def __init__(self):
        super().__init__("core")

    def configure(self, container: Container) -> None:
        # Core doesn't register anything - settings registered by Application
        pass


core_module = _CoreModule()
