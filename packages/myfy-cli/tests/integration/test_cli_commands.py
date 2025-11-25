"""
Integration tests for myfy-cli commands.

These tests verify:
- Application discovery
- Command argument parsing
- Settings resolution
- CLI output formatting
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from myfy_cli.main import app as cli_app

pytestmark = pytest.mark.integration


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def cli_runner():
    """Provide a Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_app_dir():
    """Create a temporary directory with a test application."""
    with tempfile.TemporaryDirectory() as tmpdir:
        app_file = Path(tmpdir) / "app.py"
        app_file.write_text(
            """
from myfy.core import Application
from myfy.core.config import BaseSettings
from myfy.web import WebModule, route

class AppSettings(BaseSettings):
    app_name: str = "Test App"

@route.get("/health")
async def health():
    return {"status": "ok"}

app = Application(settings_class=AppSettings, auto_discover=False)
app.add_module(WebModule())
"""
        )

        # Change to temp directory for tests
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        yield tmpdir
        os.chdir(original_dir)


@pytest.fixture
def temp_app_dir_no_app():
    """Create a temporary directory without an application."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        yield tmpdir
        os.chdir(original_dir)


# =============================================================================
# Application Discovery Tests
# =============================================================================


class TestApplicationDiscovery:
    """Test application discovery functionality."""

    def test_find_app_in_app_py(self, cli_runner, temp_app_dir):
        """Test that application is found in app.py."""
        from myfy_cli.main import find_application

        app_instance, filename, var_name = find_application()

        assert filename == "app.py"
        assert var_name == "app"

    def test_find_app_in_main_py(self, cli_runner):
        """Test that application is found in main.py."""
        with tempfile.TemporaryDirectory() as tmpdir:
            main_file = Path(tmpdir) / "main.py"
            main_file.write_text(
                """
from myfy.core import Application

application = Application(auto_discover=False)
"""
            )

            original_dir = os.getcwd()
            os.chdir(tmpdir)
            try:
                from myfy_cli.main import find_application

                app_instance, filename, var_name = find_application()
                assert filename == "main.py"
                assert var_name == "application"
            finally:
                os.chdir(original_dir)

    def test_no_app_found_exits(self, cli_runner, temp_app_dir_no_app):
        """Test that missing application causes exit."""
        with pytest.raises(SystemExit):
            from myfy_cli.main import find_application

            find_application()


# =============================================================================
# Host and Port Resolution Tests
# =============================================================================


class TestHostPortResolution:
    """Test host and port resolution logic."""

    def test_cli_args_take_precedence(self):
        """Test that CLI arguments take precedence over settings."""
        from myfy_cli.main import _resolve_host_and_port

        host, port = _resolve_host_and_port(
            host="0.0.0.0",
            port=9000,
            application=None,
        )

        assert host == "0.0.0.0"
        assert port == 9000

    def test_defaults_when_no_args(self):
        """Test default values when no arguments provided."""
        from myfy_cli.main import _resolve_host_and_port

        host, port = _resolve_host_and_port(
            host=None,
            port=None,
            application=None,
        )

        # Defaults come from WebSettings: 0.0.0.0:8000
        assert host == "0.0.0.0"
        assert port == 8000

    def test_partial_cli_args(self):
        """Test that partial CLI args work with defaults."""
        from myfy_cli.main import _resolve_host_and_port

        # Only host provided
        host, port = _resolve_host_and_port(
            host="127.0.0.1",
            port=None,
            application=None,
        )

        assert host == "127.0.0.1"
        assert port == 8000  # Default from WebSettings

        # Only port provided
        host, port = _resolve_host_and_port(
            host=None,
            port=9000,
            application=None,
        )

        assert host == "0.0.0.0"  # Default from WebSettings
        assert port == 9000


# =============================================================================
# Doctor Command Tests
# =============================================================================


class TestDoctorCommand:
    """Test the doctor command."""

    def test_doctor_success(self, cli_runner, temp_app_dir):
        """Test doctor command with valid application."""
        result = cli_runner.invoke(cli_app, ["doctor"])

        assert result.exit_code == 0
        assert "Application found" in result.output or "checks passed" in result.output

    def test_doctor_no_app(self, cli_runner, temp_app_dir_no_app):
        """Test doctor command without application."""
        result = cli_runner.invoke(cli_app, ["doctor"])

        assert result.exit_code != 0


# =============================================================================
# Routes Command Tests
# =============================================================================


class TestRoutesCommand:
    """Test the routes command."""

    def test_routes_lists_all_routes(self, cli_runner, temp_app_dir):
        """Test that routes command lists registered routes."""
        result = cli_runner.invoke(cli_app, ["routes"])

        assert result.exit_code == 0
        assert "/health" in result.output or "health" in result.output.lower()

    def test_routes_shows_method(self, cli_runner, temp_app_dir):
        """Test that routes command shows HTTP method."""
        result = cli_runner.invoke(cli_app, ["routes"])

        assert result.exit_code == 0
        assert "GET" in result.output


# =============================================================================
# Modules Command Tests
# =============================================================================


class TestModulesCommand:
    """Test the modules command."""

    def test_modules_lists_loaded_modules(self, cli_runner, temp_app_dir):
        """Test that modules command lists loaded modules."""
        result = cli_runner.invoke(cli_app, ["modules"])

        assert result.exit_code == 0
        assert "web" in result.output.lower()


# =============================================================================
# Frontend Assets Verification Tests
# =============================================================================


class TestFrontendAssetVerification:
    """Test frontend asset verification for production."""

    def test_verify_frontend_no_module(self):
        """Test that verification passes when no frontend module."""
        from myfy_cli.main import _verify_frontend_assets

        app = MagicMock()
        app._modules = []

        # Should not raise
        _verify_frontend_assets(app)

    def test_verify_frontend_with_assets(self):
        """Test that verification passes when assets exist."""
        from myfy_cli.main import _verify_frontend_assets

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create manifest
            manifest_dir = Path(tmpdir) / "frontend" / "static" / "dist" / ".vite"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "manifest.json").write_text("{}")

            original_dir = os.getcwd()
            os.chdir(tmpdir)
            try:
                frontend_module = MagicMock()
                frontend_module.name = "frontend"

                app = MagicMock()
                app._modules = [frontend_module]

                # Should not raise
                _verify_frontend_assets(app)
            finally:
                os.chdir(original_dir)

    def test_verify_frontend_missing_assets_exits(self):
        """Test that verification exits when assets missing."""
        from myfy_cli.main import _verify_frontend_assets

        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = os.getcwd()
            os.chdir(tmpdir)
            try:
                frontend_module = MagicMock()
                frontend_module.name = "frontend"

                app = MagicMock()
                app._modules = [frontend_module]

                with pytest.raises(SystemExit):
                    _verify_frontend_assets(app)
            finally:
                os.chdir(original_dir)


# =============================================================================
# Run Command Tests (without actually starting server)
# =============================================================================


class TestRunCommand:
    """Test the run command argument parsing."""

    def test_run_help(self, cli_runner):
        """Test run command help."""
        result = cli_runner.invoke(cli_app, ["run", "--help"])

        assert result.exit_code == 0
        assert "host" in result.output.lower()
        assert "port" in result.output.lower()
        assert "reload" in result.output.lower()

    def test_start_help(self, cli_runner):
        """Test start command help."""
        result = cli_runner.invoke(cli_app, ["start", "--help"])

        assert result.exit_code == 0
        assert "workers" in result.output.lower()


# =============================================================================
# Reload Module Setup Tests
# =============================================================================


class TestReloadModuleSetup:
    """Test reload module configuration."""

    def test_setup_reload_module(self):
        """Test reload module setup returns correct values."""
        from myfy_cli.main import _setup_reload_module

        import_path, env_vars = _setup_reload_module("app.py", "application")

        assert import_path == "myfy_cli.asgi_factory:create_app"
        assert env_vars["MYFY_APP_MODULE"] == "app"
        assert env_vars["MYFY_APP_VAR"] == "application"

    def test_setup_reload_module_main(self):
        """Test reload module setup with main.py."""
        from myfy_cli.main import _setup_reload_module

        import_path, env_vars = _setup_reload_module("main.py", "app")

        assert env_vars["MYFY_APP_MODULE"] == "main"
        assert env_vars["MYFY_APP_VAR"] == "app"
