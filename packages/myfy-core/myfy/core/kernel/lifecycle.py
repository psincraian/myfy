"""
Lifecycle management for modules and providers.

Handles startup/shutdown order, error recovery, and graceful termination.
"""

import asyncio
import contextlib
import logging
import signal
from contextlib import asynccontextmanager

from .module import Module


class LifecycleManager:
    """
    Manages the lifecycle of modules and the application.

    Ensures:
    - Modules start in topological order (dependencies first)
    - Modules stop in reverse order
    - Graceful shutdown with timeout
    - Error recovery during startup
    """

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._modules: list[Module] = []
        self._started_modules: list[Module] = []
        self._shutdown_event = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._logger = logging.getLogger(__name__)

    def add_module(self, module: Module) -> None:
        """Add a module to be managed."""
        self._modules.append(module)

    async def start_all(self) -> None:
        """
        Start all modules in order.

        If a module fails to start, we stop any already-started modules
        and re-raise the exception.
        """
        started_in_this_call = []

        for module in self._modules:
            try:
                await module.start()
                started_in_this_call.append(module)
                self._started_modules.append(module)
            except Exception as e:
                # Startup failed - cleanup ONLY modules we just started
                await self._emergency_stop(started_in_this_call)
                raise RuntimeError(f"Failed to start module '{module.name}': {e}") from e

    async def stop_all(self) -> None:
        """
        Stop all started modules in reverse order.

        Uses timeout to prevent hanging on shutdown.
        """
        self._logger.info(f"Stopping {len(self._started_modules)} module(s)")

        # Stop in reverse order
        for module in reversed(self._started_modules):
            try:
                self._logger.debug(f"Stopping module '{module.name}'")
                await asyncio.wait_for(module.stop(), timeout=self.timeout)
                self._logger.debug(f"Module '{module.name}' stopped successfully")
            except TimeoutError:
                self._logger.error(
                    f"Module '{module.name}' did not stop within {self.timeout}s. "
                    f"This may indicate a resource leak or hanging operation.",
                    extra={"module_name": module.name, "timeout": self.timeout},
                )
            except Exception as e:
                self._logger.exception(
                    f"Error stopping module '{module.name}': {e}",
                    extra={"module_name": module.name},
                    exc_info=True,
                )

        self._started_modules.clear()
        self._logger.info("All modules stopped")

    async def _emergency_stop(self, modules_to_stop: list[Module] | None = None) -> None:
        """
        Emergency stop during failed startup - no timeout.

        Args:
            modules_to_stop: Specific modules to stop, or None to stop all started modules
        """
        modules = modules_to_stop if modules_to_stop is not None else self._started_modules.copy()

        for module in reversed(modules):
            with contextlib.suppress(Exception):
                # Best effort - ignore errors during shutdown
                await module.stop()

            # Remove from started modules to prevent double cleanup
            if module in self._started_modules:
                self._started_modules.remove(module)

    def setup_signal_handlers(self) -> None:
        """
        Set up signal handlers for graceful shutdown.

        Handles SIGTERM and SIGINT (Ctrl+C).
        Thread-safe for asyncio event loop.
        """
        # Store the event loop for thread-safe signaling
        self._loop = asyncio.get_running_loop()

        def signal_handler(sig: int) -> None:
            print(f"\nReceived signal {sig}, initiating graceful shutdown...")
            # Thread-safe: schedule the event set in the event loop
            if self._loop and not self._loop.is_closed():
                self._loop.call_soon_threadsafe(self._shutdown_event.set)

        # Register handlers
        signal.signal(signal.SIGTERM, lambda s, _f: signal_handler(s))
        signal.signal(signal.SIGINT, lambda s, _f: signal_handler(s))

    async def wait_for_shutdown(self) -> None:
        """Wait for a shutdown signal."""
        await self._shutdown_event.wait()

    @asynccontextmanager
    async def lifespan(self):
        """
        Context manager for application lifespan.

        Usage:
            async with lifecycle_manager.lifespan():
                # Application is running
                await some_server.serve()
        """
        try:
            await self.start_all()
            yield
        finally:
            await self.stop_all()
