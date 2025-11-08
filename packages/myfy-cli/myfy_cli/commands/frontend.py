"""Frontend CLI commands for myfy."""

import sys

import klyne
import typer
from rich.console import Console

# Check if frontend module is available
try:
    from myfy.core.config import load_settings
    from myfy.frontend import BuildError, build_frontend
    from myfy.frontend.config import FrontendSettings
    from myfy.frontend.scaffold import check_frontend_initialized, scaffold_frontend

    HAS_FRONTEND = True
except ImportError:
    HAS_FRONTEND = False

frontend_app = typer.Typer(help="Frontend development commands")
console = Console()

# Timeout for npm operations (install and build)
NPM_TIMEOUT = 300  # 5 minutes


def _show_missing_module_error() -> None:
    """Display error message when frontend module is not installed."""
    console.print("[red]✗ Frontend module not installed[/red]")
    console.print("")
    console.print("The myfy-frontend package is required for this command.")
    console.print("")
    console.print("[green]Install it with:[/green]")
    console.print("  pip install myfy-frontend")
    console.print("")
    console.print("[green]Or install all optional modules:[/green]")
    console.print("  pip install myfy[all]")


def _prompt_interactive_config(
    settings: "FrontendSettings",
    templates_dir: str | None,
    static_dir: str | None,
) -> tuple[str, str]:
    """Prompt user for configuration in interactive mode."""
    console.print("[bold cyan]🎨 Frontend Initialization[/bold cyan]")
    console.print("")

    # Prompt for templates directory
    if templates_dir is None:
        templates_dir = typer.prompt(
            "Templates directory",
            default=settings.templates_dir,
            show_default=True,
        )

    # Prompt for static directory
    if static_dir is None:
        static_dir = typer.prompt(
            "Static files directory",
            default=settings.static_dir,
            show_default=True,
        )

    # Show summary and confirm
    console.print("")
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Templates: {templates_dir}")
    console.print(f"  Static:    {static_dir}")
    console.print("")

    if not typer.confirm("Proceed with initialization?", default=True):
        console.print("Cancelled.")
        raise typer.Exit(0)

    console.print("")
    return templates_dir, static_dir


def _check_already_initialized(templates_dir: str, interactive: bool) -> None:
    """Check if frontend is already initialized and prompt if needed."""
    if check_frontend_initialized(templates_dir):
        console.print("[yellow]⚠️  Frontend appears to be already initialized.[/yellow]")
        console.print(f"Found existing files in: {templates_dir}")
        console.print("")

        if interactive or typer.confirm("Continue anyway?", default=False):
            console.print("")
        else:
            console.print("Cancelled.")
            raise typer.Exit(0)


def _show_success_message() -> None:
    """Display success message and next steps."""
    console.print("")
    console.print("[green]✨ Frontend initialized successfully![/green]")
    console.print("")
    console.print("[bold]Next steps:[/bold]")
    console.print("  1. Add FrontendModule to your app:")
    console.print("")
    console.print("     [dim]from myfy.frontend import FrontendModule[/dim]")
    console.print("     [dim]app.add_module(FrontendModule())[/dim]")
    console.print("")
    console.print("  2. Run development server:")
    console.print("")
    console.print("     [dim]myfy run[/dim]")
    console.print("")
    console.print("  3. Edit templates in [cyan]frontend/templates/[/cyan]")
    console.print("")


@frontend_app.command(name="init")
def init(
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Interactive mode with prompts for configuration",
    ),
    templates_dir: str | None = typer.Option(
        None,
        "--templates-dir",
        help="Templates directory path (default: frontend/templates)",
    ),
    static_dir: str | None = typer.Option(
        None,
        "--static-dir",
        help="Static files directory path (default: frontend/static)",
    ),
) -> None:
    """
    Initialize frontend structure with Vite, Tailwind 4, and DaisyUI 5.

    Creates:
      - package.json (Vite + Tailwind + DaisyUI)
      - vite.config.js
      - frontend/templates/ (Jinja2 templates)
      - frontend/css/ (Tailwind styles)
      - frontend/js/ (JavaScript modules)
      - .gitignore

    Examples:
      myfy frontend init                    # Use defaults
      myfy frontend init -i                 # Interactive mode
      myfy frontend init --templates-dir my/templates
    """
    klyne.track(
        "myfy_frontend_init",
        {
            "interactive": interactive,
            "templates_dir": templates_dir,
            "static_dir": static_dir,
        },
    )

    # Check if frontend module is installed
    if not HAS_FRONTEND:
        _show_missing_module_error()
        sys.exit(1)

    # Load settings (respects MYFY_FRONTEND_* env vars per ADR-0002)
    settings = load_settings(FrontendSettings)

    # Interactive mode: prompt for configuration
    if interactive:
        templates_dir, static_dir = _prompt_interactive_config(settings, templates_dir, static_dir)

    # Use defaults from settings if not provided
    templates_dir = templates_dir or settings.templates_dir
    static_dir = static_dir or settings.static_dir

    # Check if already initialized
    _check_already_initialized(templates_dir, interactive)

    # Run scaffolding
    console.print("[cyan]🎨 Initializing myfy frontend...[/cyan]")
    console.print("")

    try:
        scaffold_frontend(_templates_dir=templates_dir, _static_dir=static_dir)
        _show_success_message()
    except Exception as e:
        console.print(f"[red]✗ Error initializing frontend: {e}[/red]")
        sys.exit(1)


@frontend_app.command(name="build")
def build() -> None:
    """
    Build frontend assets for production.

    Runs Vite build to generate optimized, hashed assets with manifest.json
    for cache busting.

    The build process:
      - Compiles JavaScript and CSS with Vite
      - Generates unique hashes for each asset (e.g., main-abc123.js)
      - Creates manifest.json mapping source files to hashed versions
      - Outputs to frontend/static/dist/

    Examples:
      myfy frontend build
    """
    klyne.track("myfy_frontend_build", {})

    # Check if frontend module is installed
    if not HAS_FRONTEND:
        _show_missing_module_error()
        sys.exit(1)

    # Run the build
    console.print("[cyan]🏗️  Building frontend assets...[/cyan]")
    console.print("")

    try:
        output = build_frontend(timeout=NPM_TIMEOUT)

        # Show build output
        if output:
            console.print(output)

        # Show success message
        console.print("")
        console.print("[green]✨ Build completed successfully![/green]")
        console.print("")
        console.print("[bold]Generated files:[/bold]")
        console.print("  • frontend/static/dist/.vite/manifest.json")
        console.print("  • frontend/static/dist/js/*.js (with unique hashes)")
        console.print("  • frontend/static/dist/css/*.css (with unique hashes)")
        console.print("")
        console.print("[bold]Next steps:[/bold]")
        console.print("  1. Set MYFY_FRONTEND_ENVIRONMENT=production")
        console.print("  2. Deploy your application")
        console.print("  3. Assets will be served from the manifest")

    except BuildError as e:
        console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)
