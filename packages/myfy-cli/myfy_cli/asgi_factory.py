"""
ASGI application factory for myfy CLI.

Provides a clean way to create ASGI apps with lifespan management,
eliminating the need for runtime code generation.
"""

import importlib
import os
import sys
from pathlib import Path


def create_app(
    app_module: str | None = None,
    app_var: str | None = None,
    app_dir: str | None = None,
):
    """
    Factory function for creating ASGI app with lifespan.

    This function is designed to be imported by uvicorn with --factory flag.
    It handles:
    - Dynamic application import
    - Initialization if needed
    - Lifespan integration with module lifecycle
    - ASGI app creation via factory pattern
    - Support for apps in different directories

    Args:
        app_module: Module path (e.g., "app" or "myapp.main"), defaults to env var MYFY_APP_MODULE
        app_var: Variable name in module (default: "app"), defaults to env var MYFY_APP_VAR
        app_dir: Directory containing the app, defaults to env var MYFY_APP_DIR

    Returns:
        ASGI application instance (Starlette)

    Raises:
        RuntimeError: If app_module is not provided or invalid
        RuntimeError: If app_var doesn't exist in module or is not an Application
        ImportError: If module cannot be imported

    Example:
        uvicorn myfy_cli.asgi_factory:create_app --factory \
            --env MYFY_APP_MODULE=app --env MYFY_APP_VAR=application

        # For external apps:
        uvicorn myfy_cli.asgi_factory:create_app --factory \
            --env MYFY_APP_MODULE=app --env MYFY_APP_VAR=app \
            --env MYFY_APP_DIR=/path/to/external/app
    """
    # Get module, variable, and directory from environment if not provided
    app_module = app_module or os.getenv("MYFY_APP_MODULE")
    app_var = app_var or os.getenv("MYFY_APP_VAR", "app")
    app_dir = app_dir or os.getenv("MYFY_APP_DIR")

    if not app_module:
        raise RuntimeError(
            "app_module not provided. Set MYFY_APP_MODULE environment variable "
            "or pass app_module parameter to create_app()"
        )

    # Validate app_var is a valid Python identifier
    if not app_var or not app_var.isidentifier():
        raise RuntimeError(f"Invalid app_var: '{app_var}'. Must be a valid Python identifier.")

    # If app_dir is specified, add it to the path and change to it
    if app_dir:
        app_dir_path = Path(app_dir).resolve()
        if not app_dir_path.is_dir():
            raise RuntimeError(f"App directory does not exist: {app_dir}")
        # Add app directory to Python path for imports
        app_dir_str = str(app_dir_path)
        if app_dir_str not in sys.path:
            sys.path.insert(0, app_dir_str)
    else:
        # Ensure current directory is in path for imports
        cwd = str(Path.cwd())
        if cwd not in sys.path:
            sys.path.insert(0, cwd)

    # Import the application with better error handling
    try:
        module = importlib.import_module(app_module)
    except ImportError as e:
        raise RuntimeError(
            f"Failed to import module '{app_module}': {e}\n"
            f"Make sure the module exists and is in the Python path."
        ) from e

    # Get the application variable
    try:
        application = getattr(module, app_var)
    except AttributeError as e:
        available = [name for name in dir(module) if not name.startswith("_")]
        raise RuntimeError(
            f"Variable '{app_var}' not found in module '{app_module}'.\n"
            f"Available names: {', '.join(available[:10])}"  # Show first 10
        ) from e

    # Validate it's an Application instance
    from myfy.core import Application  # noqa: PLC0415

    if not isinstance(application, Application):
        raise RuntimeError(
            f"Variable '{app_var}' in module '{app_module}' is not an Application instance.\n"
            f"Got: {type(application).__name__}"
        )

    # Use the factory pattern for clean ASGI app creation with lifespan
    # This avoids the initialization ordering issues that caused static asset 404s
    from myfy.web.factory import create_asgi_app_with_lifespan  # noqa: PLC0415

    return create_asgi_app_with_lifespan(application)
