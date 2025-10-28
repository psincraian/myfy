"""
Extension protocols for WebModule.

These protocols define contracts for modules that want to extend
the web server functionality.
"""

from typing import Protocol

from starlette.applications import Starlette
from starlette.middleware import Middleware


class IWebExtension(Protocol):
    """
    Protocol for modules that extend WebModule.

    Modules implementing this protocol can extend the ASGI application
    during the finalize() phase to add routes, mount static files, etc.

    Example:
        class FrontendModule:
            @property
            def provides(self) -> list[type]:
                return [IWebExtension]

            def finalize(self, container: Container) -> None:
                asgi_app = container.get(ASGIApp)
                self.extend_asgi_app(asgi_app.app)

            def extend_asgi_app(self, app: Starlette) -> None:
                from starlette.staticfiles import StaticFiles
                app.mount("/static", StaticFiles(directory="static"))
    """

    def extend_asgi_app(self, app: Starlette) -> None:
        """
        Extend the ASGI application.

        Called during module finalization to allow extensions to:
        - Mount static file directories
        - Add custom routes
        - Configure the ASGI app

        Args:
            app: The Starlette application instance
        """
        ...


class IMiddlewareProvider(Protocol):
    """
    Protocol for modules that provide ASGI middleware.

    Modules implementing this protocol can provide middleware
    to be added to the ASGI application stack.

    Example:
        class AuthModule:
            @property
            def provides(self) -> list[type]:
                return [IMiddlewareProvider]

            def get_middleware(self) -> list[Middleware]:
                return [
                    Middleware(AuthMiddleware, secret_key="..."),
                    Middleware(SessionMiddleware, secret_key="..."),
                ]
    """

    def get_middleware(self) -> list[Middleware]:
        """
        Return middleware to add to the ASGI app.

        Returns:
            List of Starlette Middleware instances
        """
        ...
