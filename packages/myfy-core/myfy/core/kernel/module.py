"""
Module protocol and base implementations.

Modules are the building blocks of a myfy application.
Each module (web, data, tasks, etc.) implements this protocol.
"""

from typing import Protocol, runtime_checkable
from abc import ABC, abstractmethod


@runtime_checkable
class Module(Protocol):
    """
    Protocol for a myfy module.

    Modules wire themselves into the application during startup:
    1. configure() - Register providers in DI container
    2. start() - Perform startup tasks (connect to DB, etc.)
    3. stop() - Cleanup resources gracefully
    """

    @property
    def name(self) -> str:
        """Unique name for this module (e.g., 'web', 'sqlalchemy')."""
        ...

    def configure(self, container: "Container") -> None:  # type: ignore
        """
        Configure the module by registering providers in the DI container.

        This is called during application initialization, before compilation.

        Args:
            container: The DI container to register providers in
        """
        ...

    async def start(self) -> None:
        """
        Start the module.

        Called after the container is compiled and singleton dependencies
        are available. Use this to:
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

    @abstractmethod
    def configure(self, container: "Container") -> None:  # type: ignore
        """
        Configure the module by registering providers.

        Must be implemented by subclasses.
        """
        pass

    async def start(self) -> None:
        """
        Default start implementation (no-op).

        Override if your module needs startup logic.
        """
        pass

    async def stop(self) -> None:
        """
        Default stop implementation (no-op).

        Override if your module needs cleanup logic.
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
