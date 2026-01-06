"""Tests for CLI command representation."""

import pytest

from myfy.cli.command import Command, ParamInfo


class TestParamInfo:
    """Tests for ParamInfo class."""

    def test_cli_name_converts_underscores(self):
        """Test that underscores are converted to dashes for CLI."""
        param = ParamInfo(
            name="my_param",
            type_hint=str,
            default=None,
            is_required=True,
        )
        assert param.cli_name == "my-param"

    def test_cli_name_preserves_dashes(self):
        """Test that existing dashes are preserved."""
        param = ParamInfo(
            name="my-param",
            type_hint=str,
            default=None,
            is_required=True,
        )
        assert param.cli_name == "my-param"


class TestCommand:
    """Tests for Command class."""

    def test_simple_function_command(self):
        """Test creating a command from a simple function."""

        def greet(name: str) -> None:
            print(f"Hello, {name}!")

        cmd = Command(handler=greet, name="greet")

        assert cmd.name == "greet"
        assert cmd.is_async is False
        assert len(cmd.cli_params) == 1
        assert cmd.cli_params[0].name == "name"
        assert cmd.cli_params[0].type_hint == str
        assert cmd.cli_params[0].is_required is True

    def test_command_with_default_params(self):
        """Test command with default parameter values."""

        def seed_db(count: int = 100, clear: bool = False) -> None:
            pass

        cmd = Command(handler=seed_db, name="seed-db")

        assert len(cmd.cli_params) == 2

        count_param = next(p for p in cmd.cli_params if p.name == "count")
        assert count_param.default == 100
        assert count_param.is_required is False

        clear_param = next(p for p in cmd.cli_params if p.name == "clear")
        assert clear_param.default is False
        assert clear_param.is_flag is True

    def test_async_command(self):
        """Test creating a command from an async function."""

        async def async_cmd(name: str) -> None:
            pass

        cmd = Command(handler=async_cmd, name="async-cmd")

        assert cmd.is_async is True

    def test_command_with_di_dependencies(self):
        """Test command with DI dependencies (non-primitive types)."""

        class Database:
            pass

        def process_data(count: int, db: Database) -> None:
            pass

        cmd = Command(handler=process_data, name="process-data")

        assert len(cmd.cli_params) == 1
        assert cmd.cli_params[0].name == "count"
        assert "db" in cmd.di_params

    def test_command_full_name_without_group(self):
        """Test full name for ungrouped command."""

        def my_cmd() -> None:
            pass

        cmd = Command(handler=my_cmd, name="my-cmd")

        assert cmd.full_name == "my-cmd"

    def test_command_full_name_with_group(self):
        """Test full name for grouped command."""

        def my_cmd() -> None:
            pass

        cmd = Command(handler=my_cmd, name="create", group="users")

        assert cmd.full_name == "users:create"

    def test_command_help_text(self):
        """Test command help text from docstring."""

        def documented_cmd() -> None:
            """This is the help text."""
            pass

        cmd = Command(
            handler=documented_cmd,
            name="documented",
            help_text=documented_cmd.__doc__,
        )

        assert cmd.help_text == "This is the help text."

    def test_command_repr(self):
        """Test command string representation."""

        def my_cmd(name: str, count: int = 10) -> None:
            pass

        class Service:
            pass

        def cmd_with_deps(name: str, svc: Service) -> None:
            pass

        cmd1 = Command(handler=my_cmd, name="my-cmd")
        assert "my-cmd" in repr(cmd1)
        assert "name" in repr(cmd1)
        assert "count" in repr(cmd1)

        cmd2 = Command(handler=cmd_with_deps, name="cmd-with-deps")
        assert "svc" in repr(cmd2)
