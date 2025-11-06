"""
ASGI application factory for CLI and production deployment.

Provides clean factory functions for creating ASGI apps with lifespan
management, separate from the module lifecycle system.
"""

import logging
from typing import TYPE_CHECKING, Any

from .asgi import ASGIApp
from .routing import Router

if TYPE_CHECKING:
    from starlette.applications import Starlette

    from myfy.core.kernel.app import Application

logger = logging.getLogger(__name__)


def create_asgi_app_with_lifespan(
    application: "Application",
    lifespan: Any | None = None,
) -> "Starlette":
    """
    Create ASGI application with lifespan for CLI/factory contexts.

    This function is specifically designed for scenarios where the ASGI app
    needs to be created with runtime context (like lifespan) that isn't
    available during the normal module initialization flow.

    The key difference from normal flow:
    - Normal: configure() → compile() → finalize() → start()
    - Factory: initialize() → create_asgi_app_with_lifespan() → extend

    This avoids the problem where finalize() runs before the ASGI app
    has the correct lifespan, which was causing static asset 404 errors.

    Args:
        application: The initialized Application instance
        lifespan: Optional lifespan context manager for startup/shutdown
                 If None, will use application.create_lifespan()

    Returns:
        Starlette ASGI application ready to serve

    Example:
        >>> from myfy.core import Application
        >>> from myfy.web.factory import create_asgi_app_with_lifespan
        >>>
        >>> app = Application()
        >>> app.add_module(WebModule())
        >>> app.initialize()
        >>>
        >>> asgi_app = create_asgi_app_with_lifespan(app)
        >>> # uvicorn can now serve asgi_app
    """
    from myfy.core.kernel.errors import MyfyModuleNotFoundError  # noqa: PLC0415

    from .module import WebModule  # noqa: PLC0415

    # Ensure application is initialized (safe to call multiple times)
    application.initialize()

    # Get web module and router
    try:
        _ = application.get_module(WebModule)
    except MyfyModuleNotFoundError as e:
        raise RuntimeError(
            "WebModule not found. "
            "Make sure you've added WebModule to your application:\n"
            "  app.add_module(WebModule())"
        ) from e

    router = application.container.get(Router)

    # Create lifespan if not provided
    if lifespan is None:
        lifespan = application.create_lifespan()

    # Create ASGI app with lifespan
    asgi_app = ASGIApp(application.container, router, lifespan=lifespan)
    logger.debug("Created ASGI app with lifespan")

    # Allow modules to extend the ASGI app
    # This is the clean alternative to calling finalize() twice
    _extend_asgi_app(asgi_app.app, application)

    return asgi_app.app


def _extend_asgi_app(app: "Starlette", application: "Application") -> None:
    """
    Allow modules to extend the ASGI app.

    Calls extend_asgi_app() on any modules that implement the IWebExtension
    protocol. This is used for mounting static files, adding middleware, etc.

    Args:
        app: The Starlette ASGI application
        application: The Application with modules to check
    """
    from .extensions import IWebExtension  # noqa: PLC0415

    # Use public API to get modules implementing the protocol
    extensions = application.get_modules_implementing(IWebExtension)

    for ext in extensions:
        logger.debug(f"Extending ASGI app via {ext.__class__.__name__}")
        ext.extend_asgi_app(app, application.container)

    if extensions:
        logger.info(f"Extended ASGI app via {len(extensions)} module(s)")
