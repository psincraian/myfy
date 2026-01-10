"""Tests for CliRouter and @cli.command decorator."""

import pytest
import typer

from myfy.commands.registry import CommandRegistry
from myfy.commands.router import CliRouter


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset registry before each test."""
    CommandRegistry.reset_instance()
    yield
    CommandRegistry.reset_instance()


def test_command_decorator_basic():
    """Test basic @cli.command() decorator."""
    router = CliRouter()

    @router.command()
    async def my_command():
        """My command help."""
        pass

    commands = router.get_commands()
    assert len(commands) == 1
    assert commands[0].name == "my-command"
    assert commands[0].help == "My command help."


def test_command_decorator_with_name():
    """Test @cli.command(name='custom-name')."""
    router = CliRouter()

    @router.command(name="custom-name")
    async def my_function():
        pass

    commands = router.get_commands()
    assert commands[0].name == "custom-name"


def test_command_decorator_with_group():
    """Test @cli.command(group='db')."""
    router = CliRouter()

    @router.command(group="db")
    async def seed():
        pass

    commands = router.get_commands()
    assert commands[0].group == "db"
    assert commands[0].full_name == "db:seed"


def test_group_sub_router():
    """Test cli.group() creates a scoped router."""
    router = CliRouter()
    db = router.group("db")

    @db.command()
    async def seed():
        pass

    @db.command()
    async def reset():
        pass

    commands = db.get_commands()
    assert len(commands) == 2  # noqa: PLR2004
    assert all(cmd.group == "db" for cmd in commands)


def test_primitive_type_as_option():
    """Test that primitive type with default becomes CLI option."""
    router = CliRouter()

    @router.command()
    async def seed(count: int = 10):
        pass

    commands = router.get_commands()
    cmd = commands[0]

    assert len(cmd.options) == 1
    assert cmd.options[0].name == "count"
    assert cmd.options[0].type_hint is int
    assert cmd.options[0].default == 10  # noqa: PLR2004


def test_primitive_type_without_default_as_argument():
    """Test that primitive type without default becomes CLI argument."""
    router = CliRouter()

    @router.command()
    async def import_file(filename: str):
        pass

    commands = router.get_commands()
    cmd = commands[0]

    assert len(cmd.arguments) == 1
    assert cmd.arguments[0].name == "filename"
    assert cmd.arguments[0].type_hint is str
    assert cmd.arguments[0].is_required is True


def test_complex_type_as_dependency():
    """Test that complex type becomes DI dependency."""
    router = CliRouter()

    class UserService:
        pass

    @router.command()
    async def seed(user_service: UserService, count: int = 10):
        pass

    commands = router.get_commands()
    cmd = commands[0]

    assert "user_service" in cmd.dependencies
    assert len(cmd.options) == 1  # count is an option


def test_typer_argument_annotation():
    """Test handling of typer.Argument()."""
    router = CliRouter()

    @router.command()
    async def import_data(
        file: str = typer.Argument(..., help="Input file path"),
    ):
        pass

    commands = router.get_commands()
    cmd = commands[0]

    assert len(cmd.arguments) == 1
    assert cmd.arguments[0].name == "file"
    assert cmd.arguments[0].help == "Input file path"
    assert cmd.arguments[0].is_required is True


def test_typer_option_annotation():
    """Test handling of typer.Option()."""
    router = CliRouter()

    @router.command()
    async def seed(
        count: int = typer.Option(10, "--count", "-c", help="Number of items"),
    ):
        pass

    commands = router.get_commands()
    cmd = commands[0]

    assert len(cmd.options) == 1
    assert cmd.options[0].name == "count"
    assert cmd.options[0].default == 10  # noqa: PLR2004
    assert cmd.options[0].help == "Number of items"
    assert cmd.options[0].short == "-c"


def test_mixed_parameters():
    """Test command with mixed parameter types."""
    router = CliRouter()

    class Database:
        pass

    @router.command()
    async def import_data(
        db: Database,  # DI dependency
        file: str = typer.Argument(..., help="Input file"),  # CLI argument
        batch_size: int = typer.Option(100, help="Batch size"),  # CLI option
        dry_run: bool = False,  # CLI option with default
    ):
        pass

    commands = router.get_commands()
    cmd = commands[0]

    assert "db" in cmd.dependencies
    assert len(cmd.arguments) == 1
    assert cmd.arguments[0].name == "file"
    assert len(cmd.options) == 2  # noqa: PLR2004
    option_names = {opt.name for opt in cmd.options}
    assert "batch_size" in option_names
    assert "dry_run" in option_names


def test_sync_command():
    """Test that sync commands are supported."""
    router = CliRouter()

    @router.command()
    def my_sync_command(name: str = "default"):
        return f"Hello, {name}"

    commands = router.get_commands()
    assert len(commands) == 1
    assert commands[0].name == "my-sync-command"


def test_commands_registered_in_global_registry():
    """Test that commands are registered in the global registry."""
    router = CliRouter()
    registry = CommandRegistry.get_instance()

    @router.command()
    async def test_cmd():
        pass

    assert "test-cmd" in registry
    assert registry.get("test-cmd").handler is test_cmd
