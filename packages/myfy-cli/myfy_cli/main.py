"""
CLI tools for myfy framework.

Provides commands for development and operations:
- myfy run: Start development server
- myfy routes: List all routes
- myfy modules: Show loaded modules
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from myfy.core import Application

app = typer.Typer(
    name="myfy",
    help="myfy framework CLI",
    add_completion=False,
)
console = Console()


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
    console.print(
        "Create an app.py, main.py, or application.py with an Application instance"
    )
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


def _setup_reload_module(filename: str, var_name: str) -> str:
    """
    Set up a reloadable module for uvicorn by writing a helper file.

    This creates a Python file that uvicorn can import and reload.
    The file imports the user's Application and exports the ASGI app.

    Returns the import path string (e.g., "_myfy_server:app")
    """
    # Get the module name from filename (e.g., "app.py" -> "app")
    module_name = filename.replace(".py", "")

    # Create a helper file with application reload logic
    # This file will be imported by uvicorn's worker subprocess
    helper_content = f'''"""Auto-generated reloadable module for myfy server."""
import sys
from pathlib import Path

# Add current directory to path (for worker subprocess)
_cwd = str(Path(__file__).parent)
if _cwd not in sys.path:
    sys.path.insert(0, _cwd)

# Import and initialize the application
from {module_name} import {var_name} as application

if not application._initialized:
    application.initialize()

# Get web module
web_module = None
for mod in application._modules:
    if mod.name == "web":
        web_module = mod
        break

if not web_module:
    raise RuntimeError("No web module found")

# Export ASGI app for uvicorn
_asgi_app = web_module.get_asgi_app(application.container)
app = _asgi_app.app
'''

    # Write to current directory
    helper_path = Path.cwd() / "_myfy_server.py"
    helper_path.write_text(helper_content)

    return "_myfy_server:app"


@app.command()
def run(
    host: str = typer.Option("127.0.0.1", help="Server host"),
    port: int = typer.Option(8000, help="Server port"),
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

        console.print(f"📡 Listening on http://{host}:{port}")
        console.print(f"📦 Loaded {len(application._modules)} module(s)")

        if reload:
            # Set up reloadable module for uvicorn
            import_path = _setup_reload_module(filename, var_name)
            console.print("🔄 Reload enabled - watching for file changes")

            try:
                # Use subprocess to call uvicorn CLI for proper reload support
                # This ensures the worker subprocess has the correct environment from uv
                cmd = [
                    "uvicorn",
                    import_path,
                    "--host",
                    host,
                    "--port",
                    str(port),
                    "--reload",
                    "--log-level",
                    "info",
                ]

                # Run uvicorn via subprocess (uv will handle the environment)
                subprocess.run(cmd, check=True)
            finally:
                # Clean up the temporary helper file
                helper_file = Path("_myfy_server.py")
                if helper_file.exists():
                    helper_file.unlink()
        else:
            # When reload is disabled, we can pass the app object directly
            assert web_module is not None  # Already checked above
            asgi_app = web_module.get_asgi_app(application.container)
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
            console.print(
                "[yellow]![/yellow] No web module (add WebModule() if you need HTTP)"
            )

        console.print("\n[green]✨ All checks passed![/green]")

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    app()
