"""
ASGI application factory for myfy CLI.

Provides a clean way to create ASGI apps with lifespan management,
eliminating the need for runtime code generation.
"""

import importlib
import os
import sys
from pathlib import Path

from myfy.web import WebModule


def create_app(app_module: str | None = None, app_var: str | None = None):
    """
    Factory function for creating ASGI app with lifespan.

    This function is designed to be imported by uvicorn with --factory flag.
    It handles:
    - Dynamic application import
    - Initialization if needed
    - Lifespan integration with module lifecycle
    - ASGI app creation

    Args:
        app_module: Module path (e.g., "app" or "myapp.main"), defaults to env var MYFY_APP_MODULE
        app_var: Variable name in module (default: "app"), defaults to env var MYFY_APP_VAR

    Returns:
        ASGI application instance

    Example:
        uvicorn myfy_cli.asgi_factory:create_app --factory \
            --env MYFY_APP_MODULE=app --env MYFY_APP_VAR=application
    """
    # Get module and variable from environment if not provided

    app_module = app_module or os.getenv("MYFY_APP_MODULE")
    app_var = app_var or os.getenv("MYFY_APP_VAR", "app")

    if not app_module:
        raise RuntimeError(
            "app_module not provided. Set MYFY_APP_MODULE environment variable "
            "or pass app_module parameter to create_app()"
        )

    # Ensure current directory is in path for imports
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    # Import the application
    module = importlib.import_module(app_module)
    application = getattr(module, app_var)

    # Initialize if needed
    if not application._initialized:
        application.initialize()

    try:
        web_module = application.get_module(WebModule)
    except Exception as e:
        raise RuntimeError(
            f"WebModule not found: {e}\n"
            "Make sure you've added WebModule to your application:\n"
            "  app.add_module(WebModule())"
        ) from e

    # Use centralized lifespan creation
    lifespan = application.create_lifespan()

    # Get ASGI app with lifespan
    asgi_app = web_module.get_asgi_app(application.container, lifespan=lifespan)
    return asgi_app.app
