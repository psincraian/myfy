"""
Web module for myfy.

Provides HTTP/ASGI capabilities with routing and DI-powered handlers.
"""

from myfy.core.config import load_settings

from .asgi import ASGIApp
from .config import WebSettings
from .routing import Router
from .routing import route as default_router


class WebModule:
    """
    Web module - provides HTTP server capabilities.

    Features:
    - FastAPI-like routing with @route.get/post/etc decorators
    - Automatic DI injection in handlers
    - Request-scoped dependencies
    - ASGI standard (works with uvicorn, hypercorn, etc.)
    """

    def __init__(self, router: Router | None = None):
        """
        Create web module.

        Args:
            router: Custom router (defaults to global route decorator instance)
        """
        self.router = router or default_router
        self._asgi_app: ASGIApp | None = None

    @property
    def name(self) -> str:
        return "web"

    def configure(self, container) -> None:
        """
        Configure web module.

        Registers WebSettings, Router, and ASGI app in the DI container.
        """
        # Register web settings as singleton
        web_settings = load_settings(WebSettings)
        container.register(
            type_=WebSettings,
            factory=lambda: web_settings,
            scope="singleton",
        )

        # Register router as singleton
        container.register(
            type_=Router,
            factory=lambda: self.router,
            scope="singleton",
        )

        # Register ASGI app factory
        container.register(
            type_=ASGIApp,
            factory=lambda r=self.router: ASGIApp(container, r),
            scope="singleton",
        )

    async def start(self) -> None:
        """Start web module (nothing to do - ASGI server handles this)."""

    async def stop(self) -> None:
        """Stop web module gracefully."""

    def get_asgi_app(self, container) -> ASGIApp:
        """
        Get the ASGI application.

        Called by the CLI to start the server.
        """
        if self._asgi_app is None:
            self._asgi_app = container.get(ASGIApp)
        return self._asgi_app

    def __repr__(self) -> str:
        return f"WebModule(routes={len(self.router.get_routes())})"


# Module instance for entry point
web_module = WebModule()
