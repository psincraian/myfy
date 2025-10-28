"""
Module protocol and base implementations.

Modules are the building blocks of a myfy application.
Each module (web, data, tasks, etc.) implements this protocol.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from myfy.core.di import Container


@runtime_checkable
class Module(Protocol):
    """
    Protocol for a myfy module.

    Modules wire themselves into the application during startup:
    1. configure() - Register providers in DI container
    2. extend() - Modify other modules' service registrations (optional)
    3. [Container compilation happens here]
    4. finalize() - Configure singleton services after compilation (optional)
    5. start() - Perform startup tasks (connect to DB, etc.)
    6. stop() - Cleanup resources gracefully
    """

    @property
    def name(self) -> str:
        """Unique name for this module (e.g., 'web', 'sqlalchemy')."""
        ...

    @property
    def requires(self) -> list[type]:
        """
        Module types this module depends on.

        The framework validates that all required modules are registered
        before initialization. Modules are initialized in dependency order.

        Returns:
            List of module types (e.g., [WebModule, DataModule])
            Default: [] (no dependencies)

        Example:
            @property
            def requires(self) -> list[type]:
                return [WebModule]  # FrontendModule requires WebModule
        """
        return []

    @property
    def provides(self) -> list[type]:
        """
        Extension protocols this module implements.

        Allows other modules to discover extensions via type-safe protocols.

        Returns:
            List of protocol types (e.g., [IWebExtension, IAuthProvider])
            Default: [] (no protocols)

        Example:
            @property
            def provides(self) -> list[type]:
                return [IWebExtension]  # Implements web extension protocol
        """
        return []

    def configure(self, container: Container) -> None:
        """
        Configure the module by registering providers in the DI container.

        This is called during application initialization, before compilation.
        Services are registered but not yet instantiated.

        Args:
            container: The DI container to register providers in
        """
        ...

    def extend(self, container: Container) -> None:
        """
        Extend other modules' service registrations (optional).

        Called after all modules have configured but before container compilation.
        Use this to:
        - Modify service registrations (e.g., wrap with middleware)
        - Add callbacks/hooks to other modules
        - Decorate existing service factories

        Default: no-op (most modules don't need this)

        Args:
            container: The DI container (services registered but not built)
        """

    def finalize(self, container: Container) -> None:
        """
        Finalize module configuration after container compilation (optional).

        Called after container is compiled and singletons can be resolved.
        Use this to:
        - Configure singleton services (e.g., mount static files on ASGIApp)
        - Register routes/middleware on web apps
        - Set up cross-module integrations

        Default: no-op (most modules don't need this)

        Args:
            container: The DI container (compiled, singletons accessible)
        """

    async def start(self) -> None:
        """
        Start the module.

        Called after finalize() to start runtime services.
        Use this to:
        - Connect to external services
        - Initialize background tasks
        - Warm up caches

        Must be idempotent - safe to call multiple times.
        """
        ...

    async def stop(self) -> None:
        """
        Stop the module gracefully.

        Called during application shutdown. Use this to:
        - Close database connections
        - Flush buffers
        - Cancel background tasks

        Must be idempotent - safe to call multiple times.
        """
        ...


class BaseModule(ABC):
    """
    Base implementation of the Module protocol.

    Provides default implementations and helper methods.
    """

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def requires(self) -> list[type]:
        """
        Module dependencies (default: none).

        Override to declare dependencies:
            @property
            def requires(self) -> list[type]:
                return [WebModule, DataModule]
        """
        return []

    @property
    def provides(self) -> list[type]:
        """
        Extension protocols this module implements (default: none).

        Override to declare protocols:
            @property
            def provides(self) -> list[type]:
                return [IWebExtension]
        """
        return []

    @abstractmethod
    def configure(self, container: Container) -> None:
        """
        Configure the module by registering providers.

        Must be implemented by subclasses.
        """

    def extend(self, container: Container) -> None:  # noqa: B027
        """
        Extend other modules' service registrations (optional).

        Default no-op implementation. Override if needed.
        """

    def finalize(self, container: Container) -> None:  # noqa: B027
        """
        Finalize module configuration after container compilation (optional).

        Default no-op implementation. Override if needed.
        """

    async def start(self) -> None:
        """
        Default start implementation (no-op).

        Override if your module needs startup logic.
        """
        # Default no-op implementation
        return

    async def stop(self) -> None:
        """
        Default stop implementation (no-op).

        Override if your module needs cleanup logic.
        """
        # Default no-op implementation
        return

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
