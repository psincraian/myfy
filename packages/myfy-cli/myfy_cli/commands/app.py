"""User-defined app commands for myfy.

Provides the `myfy app` command group for running user-defined CLI commands.

Usage:
    myfy app <command> [OPTIONS]
    myfy app --help

Examples:
    myfy app seed-users --count 20
    myfy app db:seed
    myfy app db:reset --force
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

# Check if commands module is available
try:
    from myfy.commands import CliModule, CommandRegistry

    HAS_COMMANDS = True
except ImportError:
    HAS_COMMANDS = False

app_commands = typer.Typer(
    help="Run user-defined CLI commands",
    invoke_without_command=True,
)
console = Console()


def _show_missing_module_error() -> None:
    """Display error message when commands module is not installed."""
    console.print("[red]Commands module not installed[/red]")
    console.print("")
    console.print("The myfy-commands package is required for this command.")
    console.print("")
    console.print("[green]Install it with:[/green]")
    console.print("  pip install myfy-commands")
    console.print("")
    console.print("[green]Or install all optional modules:[/green]")
    console.print("  pip install myfy[all]")


@app_commands.callback(invoke_without_command=True)
def run_app_command(
    ctx: typer.Context,
    command: str | None = typer.Argument(None, help="Command to run (e.g., 'seed-users')"),
    app_path: str | None = typer.Option(
        None,
        "--app-path",
        "-a",
        help="Path to app directory",
    ),
) -> None:
    """
    Run a user-defined CLI command.

    Commands are defined using the @cli.command() decorator in your app.

    Examples:
        myfy app seed-users --count 20
        myfy app db:seed
        myfy app db:reset --force
        myfy app --help
    """
    if not HAS_COMMANDS:
        _show_missing_module_error()
        sys.exit(1)

    # Handle --help or no command
    if command is None:
        _list_commands(app_path)
        return

    search_dir = Path(app_path) if app_path else None

    # Get extra args for the command
    extra_args = ctx.args if ctx.args else []

    _run_user_command(command, search_dir, extra_args)


def _run_user_command(
    command_name: str,
    search_dir: Path | None,
    extra_args: list[str],
) -> None:
    """Execute a user-defined command with full application lifecycle."""
    import klyne

    klyne.track("myfy_app_command", {"command": command_name})

    from myfy_cli.main import find_application

    # Discover and initialize application
    application, _, _ = find_application(search_dir=search_dir)

    if not application._initialized:
        application.initialize()

    # Check for CliModule
    try:
        cli_module = application.get_module(CliModule)
    except Exception:
        console.print("[red]Error: CliModule not found[/red]")
        console.print("")
        console.print("Add CliModule() to your application:")
        console.print("")
        console.print("  from myfy.commands import CliModule")
        console.print("")
        console.print("  app = Application()")
        console.print("  app.add_module(CliModule())")
        sys.exit(1)

    # Get command from registry
    registry = cli_module.get_registry()

    try:
        command = registry.get(command_name)
    except Exception:
        console.print(f"[red]Error: Command '{command_name}' not found[/red]")
        console.print("")
        _show_available_commands(registry)
        sys.exit(1)

    # Parse extra args into kwargs
    cli_args = _parse_cli_args(command, extra_args)

    # Execute with full lifecycle (start -> run -> stop)
    async def run_command() -> Any:
        await application.start()
        try:
            executor = cli_module.get_executor()
            return await executor.execute_async(command, cli_args)
        finally:
            await application.stop()

    console.print(f"[cyan]Running command: {command_name}[/cyan]")
    console.print("")

    try:
        result = asyncio.run(run_command())
        if result is not None:
            console.print(result)
    except KeyboardInterrupt:
        console.print("\n[yellow]Command interrupted[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        # Get debug mode from settings if available
        try:
            from myfy.core.config import CoreSettings

            settings = application.container.get(CoreSettings)
            if settings.debug:
                import traceback

                console.print("")
                console.print("[dim]Traceback:[/dim]")
                console.print(traceback.format_exc())
        except Exception:
            pass
        sys.exit(1)


def _list_commands(app_path: str | None) -> None:
    """List all available user commands."""
    from myfy_cli.main import find_application

    search_dir = Path(app_path) if app_path else None

    try:
        application, _, _ = find_application(search_dir=search_dir)
    except SystemExit:
        # No application found
        console.print("[yellow]No application found[/yellow]")
        console.print("")
        console.print("Create an app.py with:")
        console.print("  from myfy.core import Application")
        console.print("  from myfy.commands import CliModule")
        console.print("")
        console.print("  app = Application()")
        console.print("  app.add_module(CliModule())")
        return

    if not application._initialized:
        application.initialize()

    try:
        cli_module = application.get_module(CliModule)
    except Exception:
        console.print("[yellow]No CliModule configured[/yellow]")
        console.print("")
        console.print("Add CliModule() to your application to enable user commands.")
        return

    registry = cli_module.get_registry()
    _show_available_commands(registry)


def _show_available_commands(registry: CommandRegistry) -> None:
    """Display available commands in a table."""
    commands = registry.get_all()

    if not commands:
        console.print("[yellow]No commands registered[/yellow]")
        console.print("")
        console.print("Define commands with @cli.command():")
        console.print("")
        console.print("  from myfy.commands import cli")
        console.print("")
        console.print("  @cli.command()")
        console.print("  async def my_command(service: MyService):")
        console.print("      '''My custom command.'''")
        console.print("      ...")
        return

    table = Table(title="Available Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="green")

    for name, cmd in sorted(commands.items()):
        # Get first line of help text
        help_text = ""
        if cmd.help:
            help_text = cmd.help.strip().split("\n")[0][:60]
        table.add_row(name, help_text)

    console.print(table)
    console.print("")
    console.print(f"Total: {len(commands)} command(s)")
    console.print("")
    console.print("Run a command with: myfy app <command> [OPTIONS]")


def _parse_cli_args(command: Any, extra_args: list[str]) -> dict[str, Any]:
    """
    Parse CLI arguments for a command.

    Handles:
    - Positional arguments
    - Long options (--name value, --flag)
    - Short options (-n value, -f)
    """
    kwargs: dict[str, Any] = {}

    i = 0
    arg_idx = 0

    # Build lookup maps for options
    option_by_name: dict[str, Any] = {}
    option_by_short: dict[str, Any] = {}
    for opt in command.options:
        option_by_name[opt.name] = opt
        option_by_name[opt.name.replace("_", "-")] = opt
        if opt.short:
            option_by_short[opt.short.lstrip("-")] = opt

    while i < len(extra_args):
        arg = extra_args[i]

        if arg.startswith("--"):
            # Long option: --name value or --flag
            opt_name = arg[2:]

            # Handle --no-flag for boolean options
            if opt_name.startswith("no-"):
                actual_name = opt_name[3:].replace("-", "_")
                opt = option_by_name.get(actual_name)
                if opt and opt.type_hint == bool:
                    kwargs[actual_name] = False
                    i += 1
                    continue

            opt_name_normalized = opt_name.replace("-", "_")
            opt = option_by_name.get(opt_name) or option_by_name.get(opt_name_normalized)

            if opt and opt.type_hint == bool:
                # Boolean flag
                kwargs[opt.name] = True
            elif i + 1 < len(extra_args) and not extra_args[i + 1].startswith("-"):
                # Option with value
                value = extra_args[i + 1]
                if opt:
                    kwargs[opt.name] = _convert_value(value, opt.type_hint)
                else:
                    kwargs[opt_name_normalized] = value
                i += 1

        elif arg.startswith("-") and len(arg) > 1:
            # Short option: -n value or -f
            short_name = arg[1:]
            opt = option_by_short.get(short_name)

            if opt:
                if opt.type_hint == bool:
                    kwargs[opt.name] = True
                elif i + 1 < len(extra_args):
                    value = extra_args[i + 1]
                    kwargs[opt.name] = _convert_value(value, opt.type_hint)
                    i += 1

        else:
            # Positional argument
            if arg_idx < len(command.arguments):
                cmd_arg = command.arguments[arg_idx]
                kwargs[cmd_arg.name] = _convert_value(arg, cmd_arg.type_hint)
                arg_idx += 1

        i += 1

    # Fill in defaults for missing options
    for opt in command.options:
        if opt.name not in kwargs and opt.default is not None:
            kwargs[opt.name] = opt.default

    return kwargs


def _convert_value(value: str, type_hint: type) -> Any:
    """Convert string value to target type."""
    if type_hint == int:
        return int(value)
    if type_hint == float:
        return float(value)
    if type_hint == bool:
        return value.lower() in ("true", "1", "yes", "y")
    return value
