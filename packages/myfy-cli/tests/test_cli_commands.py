"""
Tests for CLI commands.

Tests application discovery, route listing, and command functionality.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from myfy_cli.main import (
    _load_app_from_file,
    _resolve_host_and_port,
    _setup_reload_module,
    find_application,
)


class TestFindApplication:
    """Test application discovery."""

    def test_find_app_in_app_py(self, tmp_path, monkeypatch):
        """Should find application in app.py."""
        monkeypatch.chdir(tmp_path)

        # Create app.py with Application instance
        app_file = tmp_path / "app.py"
        app_file.write_text(
            """
from myfy.core import Application

app = Application()
"""
        )

        with patch("myfy_cli.main.console"):
            with patch("myfy_cli.main._load_app_from_file") as mock_load:
                mock_app = Mock()
                mock_load.return_value = (mock_app, "app")

                result = find_application()

                assert result is not None
                assert result[0] is mock_app
                assert result[1] == "app.py"
                assert result[2] == "app"

    def test_find_app_in_main_py(self, tmp_path, monkeypatch):
        """Should find application in main.py."""
        monkeypatch.chdir(tmp_path)

        # Create main.py
        main_file = tmp_path / "main.py"
        main_file.write_text(
            """
from myfy.core import Application

application = Application()
"""
        )

        with patch("myfy_cli.main.console"):
            with patch("myfy_cli.main._load_app_from_file") as mock_load:
                mock_app = Mock()
                mock_load.return_value = (mock_app, "application")

                result = find_application()

                assert result[1] == "main.py"

    def test_find_app_checks_safe_files_only(self, tmp_path, monkeypatch):
        """Should only check whitelisted safe files."""
        monkeypatch.chdir(tmp_path)

        # Create a non-safe file
        (tmp_path / "evil.py").write_text("# malicious code")

        # Create app.py
        (tmp_path / "app.py").write_text("from myfy.core import Application\napp = Application()")

        with patch("myfy_cli.main.console"):
            with patch("myfy_cli.main._load_app_from_file") as mock_load:
                mock_load.return_value = None

                # Should not try to load evil.py
                with pytest.raises(SystemExit):
                    find_application()

    def test_exits_if_no_application_found(self, tmp_path, monkeypatch):
        """Should exit if no Application found."""
        monkeypatch.chdir(tmp_path)

        with patch("myfy_cli.main.console"):
            with pytest.raises(SystemExit):
                find_application()


class TestLoadAppFromFile:
    """Test loading application from file."""

    def test_load_app_from_valid_file(self, tmp_path):
        """Should load Application from valid file."""
        # Create test file with Application
        test_file = tmp_path / "test_app.py"
        test_file.write_text(
            """
from myfy.core import Application

my_app = Application()
"""
        )

        with patch("myfy_cli.main.console"):
            result = _load_app_from_file(str(test_file))

            assert result is not None
            app, var_name = result
            assert var_name == "my_app"

    def test_returns_none_for_invalid_file(self, tmp_path):
        """Should return None for invalid file."""
        test_file = tmp_path / "bad.py"
        test_file.write_text("this is not valid python!!! @#$")

        with patch("myfy_cli.main.console"):
            result = _load_app_from_file(str(test_file))

            assert result is None

    def test_returns_none_for_file_without_application(self, tmp_path):
        """Should return None if no Application instance found."""
        test_file = tmp_path / "no_app.py"
        test_file.write_text(
            """
# Valid Python but no Application
x = 1
y = 2
"""
        )

        with patch("myfy_cli.main.console"):
            result = _load_app_from_file(str(test_file))

            assert result is None


class TestSetupReloadModule:
    """Test reload module setup."""

    def test_setup_reload_module_returns_factory_path(self):
        """Should return factory import path."""
        import_path, env_vars = _setup_reload_module("app.py", "application")

        assert import_path == "myfy_cli.asgi_factory:create_app"
        assert "MYFY_APP_MODULE" in env_vars
        assert "MYFY_APP_VAR" in env_vars

    def test_setup_reload_module_env_vars(self):
        """Should set correct environment variables."""
        import_path, env_vars = _setup_reload_module("app.py", "app")

        assert env_vars["MYFY_APP_MODULE"] == "app"
        assert env_vars["MYFY_APP_VAR"] == "app"

    def test_setup_reload_module_strips_py_extension(self):
        """Should strip .py extension from filename."""
        import_path, env_vars = _setup_reload_module("main.py", "application")

        assert env_vars["MYFY_APP_MODULE"] == "main"


class TestResolveHostAndPort:
    """Test host and port resolution."""

    def test_uses_cli_args_if_provided(self):
        """Should use CLI arguments when provided."""
        host, port = _resolve_host_and_port("0.0.0.0", 9000)

        assert host == "0.0.0.0"
        assert port == 9000

    def test_uses_web_settings_if_cli_args_missing(self):
        """Should use WebSettings when CLI args not provided."""
        from myfy.core import Application
        from myfy.core.di.container import Container
        from myfy.core.di.scopes import SINGLETON
        from myfy.web.config import WebSettings

        # Create mock application with WebSettings
        app = Mock(spec=Application)
        container = Container()

        settings = WebSettings(host="192.168.1.1", port=8080)
        container.register(WebSettings, lambda: settings, scope=SINGLETON)
        container.compile()

        app.container = container

        host, port = _resolve_host_and_port(None, None, application=app)

        assert host == "192.168.1.1"
        assert port == 8080

    def test_falls_back_to_defaults(self):
        """Should use defaults when no config available."""
        host, port = _resolve_host_and_port(None, None, application=None)

        assert host == "127.0.0.1"
        assert port == 8000

    def test_partial_cli_args_with_settings(self):
        """Should mix CLI args with settings."""
        from myfy.core import Application
        from myfy.core.di.container import Container
        from myfy.core.di.scopes import SINGLETON
        from myfy.web.config import WebSettings

        app = Mock(spec=Application)
        container = Container()

        settings = WebSettings(host="192.168.1.1", port=8080)
        container.register(WebSettings, lambda: settings, scope=SINGLETON)
        container.compile()

        app.container = container

        # Provide only host via CLI
        host, port = _resolve_host_and_port("0.0.0.0", None, application=app)

        assert host == "0.0.0.0"  # From CLI
        assert port == 8080  # From settings

    def test_handles_missing_web_settings(self):
        """Should fall back to defaults if WebSettings unavailable."""
        from myfy.core import Application
        from myfy.core.di.container import Container

        app = Mock(spec=Application)
        container = Container()
        container.compile()
        app.container = container

        host, port = _resolve_host_and_port(None, None, application=app)

        assert host == "127.0.0.1"
        assert port == 8000


class TestVerifyFrontendAssets:
    """Test frontend asset verification."""

    def test_verify_frontend_assets_passes_if_manifest_exists(self, tmp_path, monkeypatch):
        """Should pass verification if manifest exists."""
        from myfy_cli.main import _verify_frontend_assets

        monkeypatch.chdir(tmp_path)

        # Create mock application with frontend module
        mock_app = Mock()
        mock_frontend_module = Mock()
        mock_frontend_module.name = "frontend"
        mock_app._modules = [mock_frontend_module]

        # Create manifest
        manifest_dir = tmp_path / "frontend" / "static" / "dist" / ".vite"
        manifest_dir.mkdir(parents=True)
        (manifest_dir / "manifest.json").write_text("{}")

        with patch("myfy_cli.main.console"):
            # Should not raise
            _verify_frontend_assets(mock_app)

    def test_verify_frontend_assets_exits_if_missing(self, tmp_path, monkeypatch):
        """Should exit if manifest missing."""
        from myfy_cli.main import _verify_frontend_assets

        monkeypatch.chdir(tmp_path)

        mock_app = Mock()
        mock_frontend_module = Mock()
        mock_frontend_module.name = "frontend"
        mock_app._modules = [mock_frontend_module]

        # No manifest created

        with patch("myfy_cli.main.console"):
            with pytest.raises(SystemExit):
                _verify_frontend_assets(mock_app)

    def test_verify_frontend_assets_skips_if_no_frontend(self):
        """Should skip verification if no frontend module."""
        from myfy_cli.main import _verify_frontend_assets

        mock_app = Mock()
        mock_app._modules = []  # No frontend module

        # Should not raise even though no manifest
        _verify_frontend_assets(mock_app)


class TestRunCommand:
    """Test run command functionality."""

    @patch("myfy_cli.main.klyne.track")
    @patch("myfy_cli.main.uvicorn.run")
    def test_run_with_app_path(self, mock_uvicorn_run, mock_track):
        """Should run with provided app path."""
        from typer.testing import CliRunner

        from myfy_cli.main import app

        runner = CliRunner()

        with patch("myfy_cli.main.console"):
            result = runner.invoke(
                app, ["run", "--app-path", "test:app", "--no-reload", "--host", "0.0.0.0"]
            )

            # Should call uvicorn.run
            mock_uvicorn_run.assert_called_once()


class TestRoutesCommand:
    """Test routes command functionality."""

    @patch("myfy_cli.main.klyne.track")
    @patch("myfy_cli.main.find_application")
    def test_routes_command_displays_routes(self, mock_find_app, mock_track):
        """Should display registered routes."""
        from myfy.web.routing import HTTPMethod, Route
        from typer.testing import CliRunner

        from myfy_cli.main import app

        # Mock application with web module
        mock_app = Mock()
        mock_app._initialized = True

        # Create mock web module with routes
        mock_web_module = Mock()
        mock_web_module.name = "web"

        mock_route = Route(
            path="/users", method=HTTPMethod.GET, handler=lambda: {}, name="get_users"
        )
        mock_web_module.router.get_routes.return_value = [mock_route]

        mock_app._modules = [mock_web_module]

        mock_find_app.return_value = (mock_app, "app.py", "app")

        runner = CliRunner()

        with patch("myfy_cli.main.console"):
            result = runner.invoke(app, ["routes"])

            # Command should succeed
            assert result.exit_code == 0


class TestModulesCommand:
    """Test modules command functionality."""

    @patch("myfy_cli.main.klyne.track")
    @patch("myfy_cli.main.find_application")
    def test_modules_command_displays_modules(self, mock_find_app, mock_track):
        """Should display loaded modules."""
        from typer.testing import CliRunner

        from myfy_cli.main import app

        # Mock application with modules
        mock_app = Mock()
        mock_app._initialized = True

        mock_module1 = Mock()
        mock_module1.name = "core"

        mock_module2 = Mock()
        mock_module2.name = "web"

        mock_app._modules = [mock_module1, mock_module2]

        mock_find_app.return_value = (mock_app, "app.py", "app")

        runner = CliRunner()

        with patch("myfy_cli.main.console"):
            result = runner.invoke(app, ["modules"])

            assert result.exit_code == 0
