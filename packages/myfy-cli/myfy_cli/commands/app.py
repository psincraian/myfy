"""
Application CLI commands.

Provides the `myfy app` subcommand group for running application-defined commands.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from myfy.cli.command import Command
    from myfy.core import Application

console = Console()
app_commands = typer.Typer(
    name="app",
    help="Run application-defined CLI commands",
    invoke_without_command=True,
)


def _find_application(search_dir: Path | None = None):
    """
    Discover the Application instance in a directory.

    Only checks whitelisted files for security.
    """
    import importlib.util

    from myfy.core import Application

    safe_files = ["app.py", "main.py", "application.py"]
    base_dir = search_dir or Path.cwd()

    for filename in safe_files:
        file_path = base_dir / filename
        if file_path.exists() and file_path.is_file():
            if not filename.endswith(".py"):
                continue

            try:
                # Add directory to sys.path
                file_dir = str(file_path.parent.resolve())
                path_added = False
                if file_dir not in sys.path:
                    sys.path.insert(0, file_dir)
                    path_added = True

                try:
                    spec = importlib.util.spec_from_file_location("app_module", str(file_path))
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules["app_module"] = module
                        spec.loader.exec_module(module)

                        for name in dir(module):
                            obj = getattr(module, name)
                            if isinstance(obj, Application):
                                return obj, filename, name
                finally:
                    if path_added and file_dir in sys.path:
                        sys.path.remove(file_dir)
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to load {file_path}: {e}[/yellow]")

    return None, None, None


def _get_application() -> "Application":
    """Get and initialize the application."""
    application, filename, _ = _find_application()

    if application is None:
        console.print("[red]Error: Could not find Application instance[/red]")
        console.print("Create an app.py, main.py, or application.py with an Application instance")
        raise typer.Exit(1)

    console.print(f"[green]Found application in {filename}[/green]")

    if not application._initialized:
        application.initialize()

    return application


async def _execute_command(
    cmd: "Command",
    application: "Application",
    cli_args: dict[str, Any],
) -> Any:
    """
    Execute a command with DI injection.

    Args:
        cmd: The command to execute
        application: The initialized application
        cli_args: CLI arguments parsed from user input

    Returns:
        Command result
    """
    from myfy.core.di import Container

    container = application.container

    # Build kwargs for handler
    kwargs: dict[str, Any] = {}

    # Add CLI arguments
    kwargs.update(cli_args)

    # Resolve DI dependencies
    for dep_name in cmd.di_params:
        # Get type hint for this parameter
        sig = inspect.signature(cmd.handler)
        param = sig.parameters.get(dep_name)
        if param is None:
            continue

        # Try to resolve from container
        hints = {}
        try:
            hints = dict(inspect.get_annotations(cmd.handler, eval_str=True))
        except Exception:
            pass

        dep_type = hints.get(dep_name)

        if dep_type is Application:
            kwargs[dep_name] = application
        elif dep_type is Container:
            kwargs[dep_name] = container
        elif dep_type is Console:
            kwargs[dep_name] = console
        elif dep_type is not None:
            try:
                kwargs[dep_name] = container.get(dep_type)
            except Exception as e:
                console.print(f"[red]Error resolving dependency '{dep_name}': {e}[/red]")
                raise typer.Exit(1) from e

    # Execute handler
    if cmd.is_async:
        import anyio

        return await cmd.handler(**kwargs)
    else:
        return cmd.handler(**kwargs)


def _run_command(cmd: "Command", application: "Application", cli_args: dict[str, Any]) -> None:
    """Run a command synchronously (handles async commands)."""
    import anyio

    async def run():
        # Start application lifecycle
        await application.lifecycle.start_all()
        try:
            result = await _execute_command(cmd, application, cli_args)
            if result is not None:
                console.print(result)
        finally:
            await application.lifecycle.stop_all()

    anyio.run(run)


@app_commands.callback(invoke_without_command=True)
def app_callback(ctx: typer.Context) -> None:
    """
    Run application-defined CLI commands.

    Use `myfy app --help` to see available commands.
    Use `myfy app <command> --help` for command-specific help.
    """
    if ctx.invoked_subcommand is None:
        # List available commands
        _list_commands()


def _list_commands() -> None:
    """List all available application commands."""
    from myfy.cli import CommandRegistry

    application = _get_application()

    # Check if CliModule is loaded
    has_cli = any(m.name == "cli" for m in application._modules)
    if not has_cli:
        console.print("[yellow]No CliModule found[/yellow]")
        console.print("Add CliModule() to your application to enable app commands")
        console.print("\nExample:")
        console.print("  from myfy.cli import CliModule")
        console.print("  app.add_module(CliModule())")
        return

    # Get registry
    try:
        registry = application.container.get(CommandRegistry)
    except Exception:
        registry = CommandRegistry.get_instance()

    commands = registry.get_commands()

    if not commands:
        console.print("[yellow]No commands registered[/yellow]")
        console.print("\nRegister commands using the @command decorator:")
        console.print("  from myfy.cli import command")
        console.print("")
        console.print("  @command")
        console.print("  def my_command(name: str) -> None:")
        console.print('      print(f"Hello, {name}!")')
        return

    # Create table
    table = Table(title="Application Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Parameters", style="green")

    for cmd in commands:
        # Format parameters
        params = []
        for p in cmd.cli_params:
            if p.is_required:
                params.append(f"<{p.cli_name}>")
            elif p.is_flag:
                params.append(f"[--{p.cli_name}]")
            else:
                params.append(f"[--{p.cli_name}]")

        table.add_row(
            cmd.full_name,
            (cmd.help_text or "").split("\n")[0][:50],
            " ".join(params),
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(commands)} command(s)[/dim]")
    console.print("\n[dim]Run 'myfy app <command> --help' for more info[/dim]")


@app_commands.command(name="run")
def run_command(
    command_name: str = typer.Argument(..., help="Command name to run"),
    args: list[str] | None = typer.Argument(None, help="Command arguments"),
) -> None:
    """
    Run an application command.

    Example:
        myfy app run seed-db --count 100
        myfy app run users:create admin@example.com
    """
    from myfy.cli import CommandRegistry

    application = _get_application()

    # Get registry
    try:
        registry = application.container.get(CommandRegistry)
    except Exception:
        registry = CommandRegistry.get_instance()

    # Find command
    cmd = registry.get(command_name)
    if cmd is None:
        console.print(f"[red]Error: Command '{command_name}' not found[/red]")
        console.print("\nAvailable commands:")
        for c in registry.get_commands():
            console.print(f"  - {c.full_name}")
        raise typer.Exit(1)

    # Parse arguments
    cli_args = _parse_command_args(cmd, args or [])

    # Run command
    _run_command(cmd, application, cli_args)


def _parse_command_args(cmd: "Command", args: list[str]) -> dict[str, Any]:
    """
    Parse command-line arguments for a command.

    Args:
        cmd: The command definition
        args: Raw CLI arguments

    Returns:
        Dict of parameter name -> value
    """
    result: dict[str, Any] = {}
    positional_idx = 0
    i = 0

    # Get required positional params
    positional_params = [p for p in cmd.cli_params if p.is_required and not p.is_flag]

    while i < len(args):
        arg = args[i]

        if arg.startswith("--"):
            # Named argument
            name = arg[2:]
            # Convert kebab-case to snake_case
            param_name = name.replace("-", "_")

            # Find matching parameter
            param = next((p for p in cmd.cli_params if p.name == param_name), None)

            if param is None:
                console.print(f"[yellow]Warning: Unknown option '{arg}'[/yellow]")
                i += 1
                continue

            if param.is_flag:
                # Boolean flag
                result[param_name] = True
            else:
                # Value option
                if i + 1 >= len(args):
                    console.print(f"[red]Error: Option '{arg}' requires a value[/red]")
                    raise typer.Exit(1)
                i += 1
                value = args[i]
                result[param_name] = _convert_value(value, param.type_hint)
        elif arg.startswith("-"):
            # Short option (not supported yet)
            console.print(f"[yellow]Warning: Short options not supported: '{arg}'[/yellow]")
        else:
            # Positional argument
            if positional_idx < len(positional_params):
                param = positional_params[positional_idx]
                result[param.name] = _convert_value(arg, param.type_hint)
                positional_idx += 1
            else:
                console.print(f"[yellow]Warning: Extra positional argument: '{arg}'[/yellow]")

        i += 1

    # Check required parameters
    for param in cmd.cli_params:
        if param.is_required and param.name not in result:
            console.print(f"[red]Error: Missing required parameter: {param.cli_name}[/red]")
            raise typer.Exit(1)

    # Apply defaults
    for param in cmd.cli_params:
        if param.name not in result and param.default is not None:
            result[param.name] = param.default

    return result


def _convert_value(value: str, type_hint: type | None) -> Any:
    """Convert string value to the appropriate type."""
    if type_hint is None:
        return value
    if type_hint is int:
        return int(value)
    if type_hint is float:
        return float(value)
    if type_hint is bool:
        return value.lower() in ("true", "1", "yes", "on")
    return value
