"""
Extension protocols for tasks module.

Provides ITaskProvider protocol for module dependency declaration (ADR-0005).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .queue import TaskQueue
    from .registry import TaskRegistry


@runtime_checkable
class ITaskProvider(Protocol):
    """
    Protocol for modules that provide task processing.

    Used for module dependency declaration (ADR-0005).

    Example:
        ```python
        class MyModule:
            @property
            def requires(self) -> list[type]:
                return [ITaskProvider]  # Requires tasks module
        ```
    """

    def get_queue(self) -> TaskQueue:
        """Get the task queue for enqueueing tasks."""
        ...

    def get_registry(self) -> TaskRegistry:
        """Get the task registry."""
        ...
