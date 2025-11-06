"""
Extension protocols for WebModule.

These protocols define contracts for modules that want to extend
the web server functionality.
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from starlette.applications import Starlette
from starlette.middleware import Middleware

if TYPE_CHECKING:
    from myfy.core.di import Container


@runtime_checkable
class IWebExtension(Protocol):
    """
    Protocol for modules that extend WebModule.

    Modules implementing this protocol can extend the ASGI application
    during the finalize() phase or factory creation to add routes,
    mount static files, etc.

    Example:
        class FrontendModule:
            @property
            def provides(self) -> list[type]:
                return [IWebExtension]

            def finalize(self, container: Container) -> None:
                asgi_app = container.get(ASGIApp)
                self.extend_asgi_app(asgi_app.app, container)

            def extend_asgi_app(self, app: Starlette, container: Container) -> None:
                from starlette.staticfiles import StaticFiles
                settings = container.get(MySettings)
                app.mount(settings.static_path, StaticFiles(directory="static"))
    """

    def extend_asgi_app(self, app: Starlette, container: "Container") -> None:
        """
        Extend the ASGI application.

        Called during module finalization to allow extensions to:
        - Mount static file directories
        - Add custom routes
        - Configure the ASGI app

        Args:
            app: The Starlette application instance
            container: DI container for accessing settings and services
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
