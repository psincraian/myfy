"""
CLI tools for myfy framework.

Provides commands for development and operations:
- myfy run: Start development server
- myfy routes: List all routes
- myfy modules: Show loaded modules
- myfy frontend: Frontend commands
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import klyne
import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from myfy.core import Application
from myfy.core.config import load_settings
from myfy.web.config import WebSettings
from myfy_cli.commands import frontend_app
from myfy_cli.version import __version__

klyne.init(
    api_key="klyne_9Tw9gnQoW8GX4DII8v8WmEZgfsjhgZOFMXo7C9KVhjU",
    project="myfy-cli",
    package_version=__version__,
)

app = typer.Typer(
    name="myfy",
    help="myfy framework CLI",
    add_completion=False,
)
console = Console()

# Register command groups
app.add_typer(frontend_app, name="frontend")


def find_application():
    """
    Discover the Application instance in the current directory.

    Only checks whitelisted files for security:
    - app.py
    - main.py
    - application.py

    Returns:
        tuple: (Application instance, filename, variable_name)
    """
    # Only check explicitly safe files (no glob scanning for security)
    safe_files = ["app.py", "main.py", "application.py"]

    for filename in safe_files:
        file_path = Path(filename)
        if file_path.exists() and file_path.is_file():
            # Validate it's actually a Python file
            if not filename.endswith(".py"):
                continue

            result = _load_app_from_file(str(file_path))
            if result:
                app_instance, var_name = result
                console.print(f"[green]✓ Found application in {filename}[/green]")
                return app_instance, filename, var_name

    console.print("[red]Error: Could not find Application instance[/red]")
    console.print("Create an app.py, main.py, or application.py with an Application instance")
    sys.exit(1)


def _load_app_from_file(filepath: str):
    """
    Load and return Application instance from a Python file.

    Returns:
        tuple: (Application instance, variable_name) or None
    """
    try:
        spec = importlib.util.spec_from_file_location("app_module", filepath)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules["app_module"] = module
            spec.loader.exec_module(module)

            # Look for Application instance
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, Application):
                    return obj, name
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to load {filepath}: {e}[/yellow]")

    return None


def _setup_reload_module(filename: str, var_name: str) -> tuple[str, dict[str, str]]:
    """
    Set up environment for reloadable ASGI factory.

    Instead of generating code, we use the asgi_factory module with
    environment variables to configure the application.

    Returns:
        Tuple of (import_path, env_vars)
    """
    # Get the module name from filename (e.g., "app.py" -> "app")
    module_name = filename.replace(".py", "")

    # Environment variables for the factory
    env_vars = {
        "MYFY_APP_MODULE": module_name,
        "MYFY_APP_VAR": var_name,
    }

    # Use the factory function instead of generated code
    return "myfy_cli.asgi_factory:create_app", env_vars


def _resolve_host_and_port(
    host: str | None,
    port: int | None,
    application: Application | None = None,
) -> tuple[str, int]:
    """
    Resolve host and port from CLI args, WebSettings, or defaults.

    Precedence: CLI flags > Environment variables > WebSettings defaults > Hardcoded defaults

    Args:
        host: Host from CLI (None if not provided)
        port: Port from CLI (None if not provided)
        application: Application instance (used to get WebSettings from container)

    Returns:
        Tuple of (host, port)
    """
    # If both provided via CLI, use them
    if host is not None and port is not None:
        return host, port

    # Try to get from WebSettings (respects environment variables)
    if application is not None:
        try:
            web_settings = application.container.get(WebSettings)
            if host is None:
                host = web_settings.host
            if port is None:
                port = web_settings.port
        except Exception:
            pass  # Fall through to defaults

    # If using app_path (no application), try loading WebSettings directly
    if application is None:
        try:
            web_settings = load_settings(WebSettings)
            if host is None:
                host = web_settings.host
            if port is None:
                port = web_settings.port
        except Exception:
            pass  # Fall through to defaults

    # Fall back to hardcoded defaults
    if host is None:
        host = "127.0.0.1"
    if port is None:
        port = 8000

    return host, port


@app.command()
def run(
    host: str | None = typer.Option(None, help="Server host"),
    port: int | None = typer.Option(None, help="Server port"),
    reload: bool = typer.Option(True, help="Enable auto-reload"),
    app_path: str | None = typer.Option(None, help="Path to app (e.g., main:app)"),
):
    """
    Start the development server.

    Runs the ASGI application with uvicorn.
    """
    console.print("🚀 Starting myfy development server...")

    if app_path:
        # Use provided app path
        host, port = _resolve_host_and_port(host, port, application=None)

        uvicorn.run(
            app_path,
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )
    else:
        # Auto-discover and run
        application, filename, var_name = find_application()

        # Initialize if not already done
        if not application._initialized:
            application.initialize()

        # Get ASGI app from web module
        web_module = None
        for module in application._modules:
            if module.name == "web":
                web_module = module
                break

        if web_module is None:
            console.print("[red]Error: No web module found[/red]")
            console.print("Add WebModule() to your application")
            sys.exit(1)

        # Resolve host and port (respects CLI flags > env vars > WebSettings defaults)
        host, port = _resolve_host_and_port(host, port, application)

        console.print(f"📡 Listening on http://{host}:{port}")
        console.print(f"📦 Loaded {len(application._modules)} module(s)")

        if reload:
            # Set up reloadable module for uvicorn using factory
            import_path, env_vars = _setup_reload_module(filename, var_name)
            console.print("🔄 Reload enabled - watching for file changes")

            # Use subprocess to call uvicorn CLI with environment variables
            # This ensures the worker subprocess has the correct environment
            cmd = [
                "uvicorn",
                import_path,
                "--factory",  # Tell uvicorn to call the function
                "--host",
                host,
                "--port",
                str(port),
                "--reload",
                "--log-level",
                "info",
            ]

            # Merge environment variables
            env = os.environ.copy()
            env.update(env_vars)

            # Run uvicorn via subprocess
            subprocess.run(cmd, env=env, check=True)
        else:
            # When reload is disabled, we can pass the app object directly
            assert web_module is not None  # Already checked above

            # Use centralized lifespan creation
            lifespan = application.create_lifespan()

            asgi_app = web_module.get_asgi_app(application.container, lifespan=lifespan)
            uvicorn.run(
                asgi_app.app,  # Use the underlying Starlette app
                host=host,
                port=port,
                reload=False,
                log_level="info",
            )


@app.command()
def routes():
    """
    List all registered routes.

    Shows a table of routes with methods, paths, and handler names.
    """
    application, _, _ = find_application()

    if not application._initialized:
        application.initialize()

    # Find web module
    web_module = None
    for module in application._modules:
        if module.name == "web":
            web_module = module
            break

    if web_module is None:
        console.print("[yellow]No web module found[/yellow]")
        return

    routes_list = web_module.router.get_routes()

    if not routes_list:
        console.print("[yellow]No routes registered[/yellow]")
        return

    # Create table
    table = Table(title="Registered Routes")
    table.add_column("Method", style="cyan")
    table.add_column("Path", style="magenta")
    table.add_column("Handler", style="green")
    table.add_column("Name", style="yellow")

    for route in routes_list:
        table.add_row(
            route.method.value,
            route.path,
            route.handler.__name__,
            route.name or "-",
        )

    console.print(table)
    console.print(f"\n✨ Total: {len(routes_list)} route(s)")


@app.command()
def modules():
    """
    Show all loaded modules.

    Displays modules and their configuration.
    """
    application, _, _ = find_application()

    if not application._initialized:
        application.initialize()

    # Create table
    table = Table(title="Loaded Modules")
    table.add_column("Module", style="cyan")
    table.add_column("Status", style="green")

    for module in application._modules:
        table.add_row(module.name, "loaded")

    console.print(table)
    console.print(f"\n✨ Total: {len(application._modules)} module(s)")


@app.command()
def doctor():
    """
    Validate application configuration.

    Checks for common issues and provides recommendations.
    """
    console.print("🔍 Running myfy doctor...")

    try:
        application, _, _ = find_application()

        # Try to initialize
        application.initialize()

        console.print("[green]✓[/green] Application found and initialized")
        console.print(f"[green]✓[/green] Modules loaded: {len(application._modules)}")

        # Check web module
        has_web = any(m.name == "web" for m in application._modules)
        if has_web:
            console.print("[green]✓[/green] Web module configured")
        else:
            console.print("[yellow]![/yellow] No web module (add WebModule() if you need HTTP)")

        console.print("\n[green]✨ All checks passed![/green]")

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    app()
