"""Database and migration CLI commands for myfy."""

import subprocess
import sys
from pathlib import Path

import klyne
import typer
from rich.console import Console

# Check if data module is available
try:
    from myfy.core.config import load_settings
    from myfy.data import MigrationManager, create_alembic_env_template
    from myfy.data.config import DatabaseSettings

    HAS_DATA = True
except ImportError:
    HAS_DATA = False

data_app = typer.Typer(help="Database and migration commands")
console = Console()


def _show_missing_module_error() -> None:
    """Display error message when data module is not installed."""
    console.print("[red]✗ Data module not installed[/red]")
    console.print("")
    console.print("The myfy-data package is required for this command.")
    console.print("")
    console.print("[green]Install it with:[/green]")
    console.print("  pip install myfy-data")
    console.print("")
    console.print("[green]Or install all optional modules:[/green]")
    console.print("  pip install myfy[all]")


def _check_alembic_initialized() -> bool:
    """Check if Alembic is initialized in the project."""
    return Path("alembic.ini").exists() and Path("alembic").exists()


def _show_init_success_message() -> None:
    """Display success message after initialization."""
    console.print("")
    console.print("[green]✨ Database migrations initialized![/green]")
    console.print("")
    console.print("[bold]Next steps:[/bold]")
    console.print("  1. Edit [cyan]alembic/env.py[/cyan] to import your models:")
    console.print("")
    console.print("     [dim]from myapp.models import Base[/dim]")
    console.print("     [dim]target_metadata = Base.metadata[/dim]")
    console.print("")
    console.print("  2. Create your first migration:")
    console.print("")
    console.print('     [dim]myfy data revision -m "Initial migration"[/dim]')
    console.print("")
    console.print("  3. Apply migrations:")
    console.print("")
    console.print("     [dim]myfy data upgrade[/dim]")
    console.print("")


@data_app.command(name="init")
def init(
    directory: str = typer.Option(
        "alembic",
        "--directory",
        "-d",
        help="Directory name for Alembic migrations",
    ),
) -> None:
    """
    Initialize Alembic for database migrations.

    Creates:
      - alembic.ini (configuration file)
      - alembic/ (migrations directory)
      - alembic/versions/ (migration scripts)
      - alembic/env.py (async-compatible environment)

    Examples:
      myfy data init                    # Use default 'alembic' directory
      myfy data init -d migrations      # Use custom directory
    """
    klyne.track("myfy_data_init", {"directory": directory})

    if not HAS_DATA:
        _show_missing_module_error()
        sys.exit(1)

    # Check if already initialized
    if _check_alembic_initialized():
        console.print("[yellow]⚠️  Alembic appears to be already initialized.[/yellow]")
        console.print("Found existing alembic.ini and alembic/ directory.")
        console.print("")
        if not typer.confirm(
            "Continue anyway? (this will overwrite existing files)", default=False
        ):
            console.print("Cancelled.")
            raise typer.Exit(0)
        console.print("")

    console.print("[cyan]🗄️  Initializing database migrations...[/cyan]")
    console.print("")

    try:
        # Initialize Alembic
        manager = MigrationManager(alembic_dir=Path(directory))
        manager.init()

        # Load settings to get database URL
        settings = load_settings(DatabaseSettings)

        # Generate async-compatible env.py
        env_content = create_alembic_env_template(settings.database_url)
        env_path = Path(directory) / "env.py"
        env_path.write_text(env_content)

        console.print(f"[green]✓[/green] Created {directory}/")
        console.print("[green]✓[/green] Created alembic.ini")
        console.print(f"[green]✓[/green] Updated {directory}/env.py (async-compatible)")

        _show_init_success_message()

    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to initialize Alembic: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


@data_app.command(name="revision")
def revision(
    message: str = typer.Option(
        ...,
        "--message",
        "-m",
        help="Migration message/description",
    ),
    autogenerate: bool = typer.Option(
        True,
        "--autogenerate/--no-autogenerate",
        help="Auto-detect model changes",
    ),
) -> None:
    """
    Create a new migration revision.

    Generates a migration script in alembic/versions/ based on model changes.

    Examples:
      myfy data revision -m "Add users table"
      myfy data revision -m "Add email column" --autogenerate
      myfy data revision -m "Manual migration" --no-autogenerate
    """
    klyne.track("myfy_data_revision", {"message": message, "autogenerate": autogenerate})

    if not HAS_DATA:
        _show_missing_module_error()
        sys.exit(1)

    if not _check_alembic_initialized():
        console.print("[red]✗ Alembic not initialized[/red]")
        console.print("")
        console.print("Run [cyan]myfy data init[/cyan] first to set up migrations.")
        sys.exit(1)

    console.print(f"[cyan]📝 Creating migration: {message}[/cyan]")
    console.print("")

    try:
        manager = MigrationManager()
        manager.revision(message=message, autogenerate=autogenerate)

        console.print("")
        console.print("[green]✨ Migration created![/green]")
        console.print("")
        console.print("[bold]Next steps:[/bold]")
        console.print("  1. Review the migration in [cyan]alembic/versions/[/cyan]")
        console.print("  2. Apply with: [dim]myfy data upgrade[/dim]")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to create migration: {e}[/red]")
        sys.exit(1)


@data_app.command(name="upgrade")
def upgrade(
    revision: str = typer.Argument(
        "head",
        help="Target revision (default: 'head' for latest)",
    ),
) -> None:
    """
    Upgrade database to a specific revision.

    Applies pending migrations to bring the database schema up to date.

    Examples:
      myfy data upgrade              # Upgrade to latest
      myfy data upgrade head         # Same as above
      myfy data upgrade +1           # Upgrade one revision
      myfy data upgrade abc123       # Upgrade to specific revision
    """
    klyne.track("myfy_data_upgrade", {"revision": revision})

    if not HAS_DATA:
        _show_missing_module_error()
        sys.exit(1)

    if not _check_alembic_initialized():
        console.print("[red]✗ Alembic not initialized[/red]")
        console.print("")
        console.print("Run [cyan]myfy data init[/cyan] first to set up migrations.")
        sys.exit(1)

    console.print(f"[cyan]⬆️  Upgrading database to: {revision}[/cyan]")
    console.print("")

    try:
        manager = MigrationManager()
        manager.upgrade(revision=revision)

        console.print("")
        console.print("[green]✨ Database upgraded successfully![/green]")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to upgrade database: {e}[/red]")
        sys.exit(1)


@data_app.command(name="downgrade")
def downgrade(
    revision: str = typer.Argument(
        "-1",
        help="Target revision (default: '-1' for one step back)",
    ),
) -> None:
    """
    Downgrade database to a previous revision.

    Reverts migrations to roll back schema changes.

    Examples:
      myfy data downgrade            # Downgrade one revision
      myfy data downgrade -1         # Same as above
      myfy data downgrade -2         # Downgrade two revisions
      myfy data downgrade abc123     # Downgrade to specific revision
      myfy data downgrade base       # Downgrade to initial state
    """
    klyne.track("myfy_data_downgrade", {"revision": revision})

    if not HAS_DATA:
        _show_missing_module_error()
        sys.exit(1)

    if not _check_alembic_initialized():
        console.print("[red]✗ Alembic not initialized[/red]")
        console.print("")
        console.print("Run [cyan]myfy data init[/cyan] first to set up migrations.")
        sys.exit(1)

    # Warn about downgrade
    console.print("[yellow]⚠️  Warning: Downgrading may result in data loss![/yellow]")
    console.print("")
    if not typer.confirm(f"Downgrade to revision '{revision}'?", default=False):
        console.print("Cancelled.")
        raise typer.Exit(0)

    console.print("")
    console.print(f"[cyan]⬇️  Downgrading database to: {revision}[/cyan]")
    console.print("")

    try:
        manager = MigrationManager()
        manager.downgrade(revision=revision)

        console.print("")
        console.print("[green]✨ Database downgraded successfully![/green]")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to downgrade database: {e}[/red]")
        sys.exit(1)


@data_app.command(name="current")
def current() -> None:
    """
    Show current database revision.

    Displays the revision that the database is currently at.

    Examples:
      myfy data current
    """
    klyne.track("myfy_data_current", {})

    if not HAS_DATA:
        _show_missing_module_error()
        sys.exit(1)

    if not _check_alembic_initialized():
        console.print("[red]✗ Alembic not initialized[/red]")
        console.print("")
        console.print("Run [cyan]myfy data init[/cyan] first to set up migrations.")
        sys.exit(1)

    console.print("[cyan]📍 Current database revision:[/cyan]")
    console.print("")

    try:
        manager = MigrationManager()
        manager.current()

    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to get current revision: {e}[/red]")
        sys.exit(1)


@data_app.command(name="history")
def history() -> None:
    """
    Show migration history.

    Displays all migrations in the project.

    Examples:
      myfy data history
    """
    klyne.track("myfy_data_history", {})

    if not HAS_DATA:
        _show_missing_module_error()
        sys.exit(1)

    if not _check_alembic_initialized():
        console.print("[red]✗ Alembic not initialized[/red]")
        console.print("")
        console.print("Run [cyan]myfy data init[/cyan] first to set up migrations.")
        sys.exit(1)

    console.print("[cyan]📜 Migration history:[/cyan]")
    console.print("")

    try:
        manager = MigrationManager()
        manager.history()

    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to get migration history: {e}[/red]")
        sys.exit(1)
