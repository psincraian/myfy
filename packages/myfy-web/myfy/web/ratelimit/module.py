"""
Rate limiting module for myfy.

Integrates rate limiting with the myfy module system.
"""

from typing import TYPE_CHECKING

from starlette.middleware import Middleware

from myfy.core.config import load_settings
from myfy.core.di import REQUEST, SINGLETON

from ..extensions import IMiddlewareProvider
from .config import RateLimitSettings
from .context import RateLimitContext
from .store import InMemoryRateLimitStore, RateLimitStore

if TYPE_CHECKING:
    from myfy.core.di import Container


class RateLimitModule:
    """
    Rate limiting module.

    Provides:
    - Global rate limiting via middleware
    - Per-route rate limiting via @rate_limit decorator
    - RateLimitContext for dynamic key override
    - Configurable storage backends

    Usage:
        from myfy.core import Application
        from myfy.web import WebModule
        from myfy.web.ratelimit import RateLimitModule

        app = Application()
        app.add_module(WebModule())
        app.add_module(RateLimitModule())

    Configuration (environment variables):
        MYFY_RATELIMIT_ENABLED=true
        MYFY_RATELIMIT_DEFAULT_REQUESTS=100
        MYFY_RATELIMIT_DEFAULT_WINDOW_SECONDS=60
        MYFY_RATELIMIT_GLOBAL_REQUESTS=1000
        MYFY_RATELIMIT_BACKEND=memory
    """

    def __init__(
        self,
        settings: RateLimitSettings | None = None,
        store: RateLimitStore | None = None,
    ):
        """
        Create rate limit module.

        Args:
            settings: Rate limit settings (defaults to loading from env)
            store: Custom storage backend (defaults to in-memory)
        """
        self._settings = settings
        self._store = store
        self._owned_store: InMemoryRateLimitStore | None = None

    @property
    def name(self) -> str:
        return "ratelimit"

    @property
    def requires(self) -> list[type]:
        # Depends on WebModule for middleware integration
        from ..module import WebModule  # noqa: PLC0415

        return [WebModule]

    @property
    def provides(self) -> list[type]:
        return [IMiddlewareProvider]

    def configure(self, container: "Container") -> None:
        """Register rate limit services in DI container."""
        from myfy.core.di.types import ProviderKey  # noqa: PLC0415

        # Load or use provided settings
        settings = self._settings
        if settings is None:
            key = ProviderKey(RateLimitSettings)
            # Only load settings if not already registered (e.g., from nested app settings)
            if key not in container._providers:
                settings = load_settings(RateLimitSettings)

        if settings is not None:
            container.register(
                type_=RateLimitSettings,
                factory=lambda s=settings: s,
                scope=SINGLETON,
            )

        # Register or use provided store
        if self._store is not None:
            container.register(
                type_=RateLimitStore,
                factory=lambda: self._store,
                scope=SINGLETON,
            )
        else:
            # Create default in-memory store
            self._owned_store = InMemoryRateLimitStore()
            container.register(
                type_=RateLimitStore,
                factory=lambda: self._owned_store,
                scope=SINGLETON,
            )

        # Register RateLimitContext as request-scoped
        container.register(
            type_=RateLimitContext,
            factory=lambda: RateLimitContext(),
            scope=REQUEST,
        )

    def extend(self, container: "Container") -> None:
        """Extend other modules (no-op)."""

    def finalize(self, container: "Container") -> None:
        """Finalize module configuration (no-op)."""

    def get_middleware(self) -> list[Middleware]:
        """Return rate limit middleware for ASGI stack."""
        from .middleware import RateLimitMiddleware  # noqa: PLC0415

        # Middleware will get store and settings from DI container
        # We need to return a factory that the ASGI builder can use
        # For now, use the module's references
        if self._store is None and self._owned_store is None:
            # Store not created yet - will be created in configure()
            self._owned_store = InMemoryRateLimitStore()

        store = self._store or self._owned_store
        settings = self._settings or load_settings(RateLimitSettings)

        return [
            Middleware(
                RateLimitMiddleware,
                store=store,
                settings=settings,
            )
        ]

    async def start(self) -> None:
        """Start background tasks (cleanup for in-memory store)."""
        if self._owned_store is not None:
            await self._owned_store.start()

    async def stop(self) -> None:
        """Stop background tasks."""
        if self._owned_store is not None:
            await self._owned_store.stop()

    def __repr__(self) -> str:
        return f"RateLimitModule(enabled={self._settings.enabled if self._settings else 'default'})"
