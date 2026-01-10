"""User management CLI commands for myfy."""

from __future__ import annotations

import asyncio
import getpass
import sys
from pathlib import Path

import klyne
import typer
from rich.console import Console
from rich.table import Table

# Check if user module is available
try:
    from myfy.user import UserModule, UserService
    from myfy.user.templates.scaffold import TemplateScaffolder

    HAS_USER = True
except ImportError:
    HAS_USER = False

user_app = typer.Typer(help="User management commands")
console = Console()


def _show_missing_module_error() -> None:
    """Display error message when user module is not installed."""
    console.print("[red]x User module not installed[/red]")
    console.print("")
    console.print("The myfy-user package is required for this command.")
    console.print("")
    console.print("[green]Install it with:[/green]")
    console.print("  pip install myfy-user")
    console.print("")
    console.print("[green]Or install all optional modules:[/green]")
    console.print("  pip install myfy[all]")


def _find_application():
    """Find and return the application instance."""
    # Import here to avoid circular imports
    from myfy_cli.main import find_application

    return find_application()


def _get_user_service(application) -> UserService:
    """Get UserService from application container."""
    if not application._initialized:
        application.initialize()

    # Find UserModule
    user_module = None
    for module in application._modules:
        if isinstance(module, UserModule):
            user_module = module
            break

    if user_module is None:
        console.print("[red]x UserModule not found in application[/red]")
        console.print("")
        console.print("Add UserModule() to your application:")
        console.print("")
        console.print("  from myfy.user import UserModule")
        console.print("")
        console.print("  app.add_module(UserModule())")
        sys.exit(1)

    return application.container.get(UserService)


@user_app.command(name="init")
def init(
    templates_dir: str = typer.Option(
        "templates/user",
        "--templates-dir",
        "-t",
        help="Directory for user templates",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing templates",
    ),
) -> None:
    """
    Initialize user templates for customization.

    Scaffolds user authentication templates to your project for customization.
    Templates include login, register, password reset, and profile pages.

    Examples:
      myfy user init                     # Use default templates/user directory
      myfy user init -t auth/templates   # Use custom directory
      myfy user init --force             # Overwrite existing templates
    """
    klyne.track("myfy_user_init", {"templates_dir": templates_dir, "force": force})

    if not HAS_USER:
        _show_missing_module_error()
        sys.exit(1)

    templates_path = Path(templates_dir)

    # Check if templates already exist
    if templates_path.exists() and not force:
        console.print(f"[yellow]! Templates directory already exists: {templates_path}[/yellow]")
        console.print("")
        if not typer.confirm("Overwrite existing templates?", default=False):
            console.print("Cancelled.")
            raise typer.Exit(0)
        console.print("")

    console.print(f"[cyan]Scaffolding user templates to {templates_path}...[/cyan]")
    console.print("")

    try:
        scaffolder = TemplateScaffolder()
        created_files = scaffolder.scaffold_templates(templates_path, overwrite=force)

        for file_path in created_files:
            console.print(f"[green]v[/green] Created {file_path}")

        console.print("")
        console.print("[green]User templates initialized![/green]")
        console.print("")
        console.print("[bold]Next steps:[/bold]")
        console.print(f"  1. Customize templates in [cyan]{templates_path}[/cyan]")
        console.print("  2. Configure UserModule to use your templates:")
        console.print("")
        console.print("     UserModule(")
        console.print(f'         templates_path="{templates_path}",')
        console.print("     )")
        console.print("")

    except Exception as e:
        console.print(f"[red]x Failed to scaffold templates: {e}[/red]")
        sys.exit(1)


@user_app.command(name="create-admin")
def create_admin(
    email: str = typer.Option(
        ...,
        "--email",
        "-e",
        help="Admin email address",
    ),
    password: str | None = typer.Option(
        None,
        "--password",
        "-p",
        help="Admin password (prompted if not provided)",
    ),
) -> None:
    """
    Create an admin user.

    Creates a new user with superuser privileges.

    Examples:
      myfy user create-admin -e admin@example.com
      myfy user create-admin -e admin@example.com -p secretpassword
    """
    klyne.track("myfy_user_create_admin", {"email": email})

    if not HAS_USER:
        _show_missing_module_error()
        sys.exit(1)

    # Prompt for password if not provided
    if password is None:
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirm password: ")

        if password != password_confirm:
            console.print("[red]x Passwords do not match[/red]")
            sys.exit(1)

    if len(password) < 8:
        console.print("[red]x Password must be at least 8 characters[/red]")
        sys.exit(1)

    console.print(f"[cyan]Creating admin user: {email}[/cyan]")
    console.print("")

    try:
        application, _, _ = _find_application()
        user_service = _get_user_service(application)

        async def _create_admin():
            # Check if user already exists
            existing = await user_service.get_by_email(email)
            if existing:
                console.print(f"[yellow]! User already exists: {email}[/yellow]")
                if not typer.confirm("Make this user an admin?", default=False):
                    console.print("Cancelled.")
                    raise typer.Exit(0)

                # Update to superuser
                await user_service.update(
                    existing.id,
                    is_superuser=True,
                    email_verified=True,
                )
                console.print(f"[green]v[/green] Updated {email} to admin")
                return

            # Create new admin user
            user = await user_service.create(
                email=email,
                password=password,
                is_superuser=True,
                email_verified=True,  # Skip email verification for CLI-created admins
            )

            console.print(f"[green]v[/green] Created admin user: {user.email}")
            console.print(f"[green]v[/green] User ID: {user.id}")

        asyncio.run(_create_admin())

        console.print("")
        console.print("[green]Admin user created successfully![/green]")

    except Exception as e:
        console.print(f"[red]x Failed to create admin: {e}[/red]")
        sys.exit(1)


@user_app.command(name="list")
def list_users(
    admins_only: bool = typer.Option(
        False,
        "--admins-only",
        "-a",
        help="Show only admin users",
    ),
    limit: int = typer.Option(
        50,
        "--limit",
        "-l",
        help="Maximum number of users to show",
    ),
) -> None:
    """
    List users.

    Displays a table of registered users.

    Examples:
      myfy user list                 # List all users
      myfy user list --admins-only   # List only admins
      myfy user list -l 100          # List up to 100 users
    """
    klyne.track("myfy_user_list", {"admins_only": admins_only, "limit": limit})

    if not HAS_USER:
        _show_missing_module_error()
        sys.exit(1)

    try:
        application, _, _ = _find_application()
        user_service = _get_user_service(application)

        async def _list_users():
            if admins_only:
                return await user_service.list_admins(limit=limit)
            return await user_service.list_users(limit=limit)

        users = asyncio.run(_list_users())

        if not users:
            if admins_only:
                console.print("[yellow]No admin users found[/yellow]")
            else:
                console.print("[yellow]No users found[/yellow]")
            return

        # Create table
        table = Table(title="Users" if not admins_only else "Admin Users")
        table.add_column("ID", style="dim", max_width=36)
        table.add_column("Email", style="cyan")
        table.add_column("Verified", style="green")
        table.add_column("Active", style="green")
        table.add_column("Admin", style="yellow")
        table.add_column("Created", style="dim")

        for user in users:
            table.add_row(
                user.id[:8] + "...",
                user.email,
                "Yes" if user.email_verified else "No",
                "Yes" if user.is_active else "No",
                "Yes" if user.is_superuser else "No",
                user.created_at.strftime("%Y-%m-%d") if user.created_at else "-",
            )

        console.print(table)
        console.print(f"\nTotal: {len(users)} user(s)")

    except Exception as e:
        console.print(f"[red]x Failed to list users: {e}[/red]")
        sys.exit(1)


@user_app.command(name="reset-password")
def reset_password(
    email: str = typer.Option(
        ...,
        "--email",
        "-e",
        help="User email address",
    ),
    password: str | None = typer.Option(
        None,
        "--password",
        "-p",
        help="New password (prompted if not provided)",
    ),
) -> None:
    """
    Reset a user's password.

    Directly sets a new password for the user (bypasses email flow).

    Examples:
      myfy user reset-password -e user@example.com
      myfy user reset-password -e user@example.com -p newpassword
    """
    klyne.track("myfy_user_reset_password", {"email": email})

    if not HAS_USER:
        _show_missing_module_error()
        sys.exit(1)

    # Prompt for password if not provided
    if password is None:
        password = getpass.getpass("New password: ")
        password_confirm = getpass.getpass("Confirm password: ")

        if password != password_confirm:
            console.print("[red]x Passwords do not match[/red]")
            sys.exit(1)

    if len(password) < 8:
        console.print("[red]x Password must be at least 8 characters[/red]")
        sys.exit(1)

    console.print(f"[cyan]Resetting password for: {email}[/cyan]")
    console.print("")

    try:
        application, _, _ = _find_application()
        user_service = _get_user_service(application)

        async def _reset_password():
            user = await user_service.get_by_email(email)
            if not user:
                console.print(f"[red]x User not found: {email}[/red]")
                sys.exit(1)

            assert user is not None  # Type narrowing after sys.exit
            await user_service.set_password(user.id, password)
            console.print(f"[green]v[/green] Password reset for: {email}")

        asyncio.run(_reset_password())

        console.print("")
        console.print("[green]Password reset successfully![/green]")

    except Exception as e:
        console.print(f"[red]x Failed to reset password: {e}[/red]")
        sys.exit(1)


@user_app.command(name="deactivate")
def deactivate(
    email: str = typer.Option(
        ...,
        "--email",
        "-e",
        help="User email address",
    ),
) -> None:
    """
    Deactivate a user account.

    Prevents the user from logging in without deleting their data.

    Examples:
      myfy user deactivate -e user@example.com
    """
    klyne.track("myfy_user_deactivate", {"email": email})

    if not HAS_USER:
        _show_missing_module_error()
        sys.exit(1)

    console.print(f"[yellow]! Deactivating user: {email}[/yellow]")
    console.print("")

    if not typer.confirm("Are you sure you want to deactivate this user?", default=False):
        console.print("Cancelled.")
        raise typer.Exit(0)

    try:
        application, _, _ = _find_application()
        user_service = _get_user_service(application)

        async def _deactivate():
            user = await user_service.get_by_email(email)
            if not user:
                console.print(f"[red]x User not found: {email}[/red]")
                sys.exit(1)

            assert user is not None  # Type narrowing after sys.exit
            if not user.is_active:
                console.print(f"[yellow]! User is already deactivated: {email}[/yellow]")
                return

            await user_service.update(user.id, is_active=False)
            console.print(f"[green]v[/green] Deactivated user: {email}")

        asyncio.run(_deactivate())

        console.print("")
        console.print("[green]User deactivated successfully![/green]")

    except Exception as e:
        console.print(f"[red]x Failed to deactivate user: {e}[/red]")
        sys.exit(1)


@user_app.command(name="activate")
def activate(
    email: str = typer.Option(
        ...,
        "--email",
        "-e",
        help="User email address",
    ),
) -> None:
    """
    Reactivate a deactivated user account.

    Allows the user to log in again.

    Examples:
      myfy user activate -e user@example.com
    """
    klyne.track("myfy_user_activate", {"email": email})

    if not HAS_USER:
        _show_missing_module_error()
        sys.exit(1)

    console.print(f"[cyan]Activating user: {email}[/cyan]")
    console.print("")

    try:
        application, _, _ = _find_application()
        user_service = _get_user_service(application)

        async def _activate():
            user = await user_service.get_by_email(email)
            if not user:
                console.print(f"[red]x User not found: {email}[/red]")
                sys.exit(1)

            assert user is not None  # Type narrowing after sys.exit
            if user.is_active:
                console.print(f"[yellow]! User is already active: {email}[/yellow]")
                return

            await user_service.update(user.id, is_active=True)
            console.print(f"[green]v[/green] Activated user: {email}")

        asyncio.run(_activate())

        console.print("")
        console.print("[green]User activated successfully![/green]")

    except Exception as e:
        console.print(f"[red]x Failed to activate user: {e}[/red]")
        sys.exit(1)


@user_app.command(name="verify-email")
def verify_email(
    email: str = typer.Option(
        ...,
        "--email",
        "-e",
        help="User email address",
    ),
) -> None:
    """
    Manually verify a user's email.

    Marks the user's email as verified without requiring token confirmation.

    Examples:
      myfy user verify-email -e user@example.com
    """
    klyne.track("myfy_user_verify_email", {"email": email})

    if not HAS_USER:
        _show_missing_module_error()
        sys.exit(1)

    console.print(f"[cyan]Verifying email for: {email}[/cyan]")
    console.print("")

    try:
        application, _, _ = _find_application()
        user_service = _get_user_service(application)

        async def _verify():
            user = await user_service.get_by_email(email)
            if not user:
                console.print(f"[red]x User not found: {email}[/red]")
                sys.exit(1)

            assert user is not None  # Type narrowing after sys.exit
            if user.email_verified:
                console.print(f"[yellow]! Email already verified: {email}[/yellow]")
                return

            await user_service.update(user.id, email_verified=True)
            console.print(f"[green]v[/green] Email verified for: {email}")

        asyncio.run(_verify())

        console.print("")
        console.print("[green]Email verified successfully![/green]")

    except Exception as e:
        console.print(f"[red]x Failed to verify email: {e}[/red]")
        sys.exit(1)
