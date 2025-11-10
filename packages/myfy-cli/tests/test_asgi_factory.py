"""
Tests for ASGI application factory.

Tests dynamic application loading and ASGI app creation.
"""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from myfy_cli.asgi_factory import create_app


class TestCreateAppConfiguration:
    """Test app creation configuration."""

    def test_requires_app_module(self):
        """Should require app_module parameter or env var."""
        with pytest.raises(RuntimeError, match="app_module not provided"):
            create_app()

    def test_app_module_from_parameter(self):
        """Should use app_module from parameter."""
        with patch("myfy_cli.asgi_factory.importlib.import_module") as mock_import:
            with patch("myfy_cli.asgi_factory.getattr") as mock_getattr:
                # Mock the Application instance
                from myfy.core import Application

                mock_app = Mock(spec=Application)
                mock_getattr.return_value = mock_app

                with patch(
                    "myfy_cli.asgi_factory.create_asgi_app_with_lifespan"
                ) as mock_create_asgi:
                    create_app(app_module="test_app", app_var="app")

                    mock_import.assert_called_once_with("test_app")

    def test_app_module_from_env(self, monkeypatch):
        """Should use app_module from environment variable."""
        monkeypatch.setenv("MYFY_APP_MODULE", "env_app")

        with patch("myfy_cli.asgi_factory.importlib.import_module") as mock_import:
            with patch("myfy_cli.asgi_factory.getattr") as mock_getattr:
                from myfy.core import Application

                mock_app = Mock(spec=Application)
                mock_getattr.return_value = mock_app

                with patch("myfy_cli.asgi_factory.create_asgi_app_with_lifespan"):
                    create_app()

                    mock_import.assert_called_once_with("env_app")

    def test_app_var_defaults_to_app(self, monkeypatch):
        """Should default app_var to 'app'."""
        monkeypatch.setenv("MYFY_APP_MODULE", "test_app")

        with patch("myfy_cli.asgi_factory.importlib.import_module"):
            with patch("myfy_cli.asgi_factory.getattr") as mock_getattr:
                from myfy.core import Application

                mock_app = Mock(spec=Application)
                mock_getattr.return_value = mock_app

                with patch("myfy_cli.asgi_factory.create_asgi_app_with_lifespan"):
                    create_app()

                    # Should try to get 'app' attribute
                    assert mock_getattr.call_args[0][1] == "app"

    def test_app_var_from_env(self, monkeypatch):
        """Should use app_var from environment variable."""
        monkeypatch.setenv("MYFY_APP_MODULE", "test_app")
        monkeypatch.setenv("MYFY_APP_VAR", "application")

        with patch("myfy_cli.asgi_factory.importlib.import_module"):
            with patch("myfy_cli.asgi_factory.getattr") as mock_getattr:
                from myfy.core import Application

                mock_app = Mock(spec=Application)
                mock_getattr.return_value = mock_app

                with patch("myfy_cli.asgi_factory.create_asgi_app_with_lifespan"):
                    create_app()

                    assert mock_getattr.call_args[0][1] == "application"

    def test_invalid_app_var_raises_error(self, monkeypatch):
        """Should raise error for invalid app_var."""
        monkeypatch.setenv("MYFY_APP_MODULE", "test_app")

        with pytest.raises(RuntimeError, match="Invalid app_var"):
            create_app(app_var="123-invalid")


class TestCreateAppImport:
    """Test application module import."""

    def test_import_module_success(self, monkeypatch):
        """Should import module successfully."""
        monkeypatch.setenv("MYFY_APP_MODULE", "test_app")

        with patch("myfy_cli.asgi_factory.importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module

            with patch("myfy_cli.asgi_factory.getattr") as mock_getattr:
                from myfy.core import Application

                mock_app = Mock(spec=Application)
                mock_getattr.return_value = mock_app

                with patch("myfy_cli.asgi_factory.create_asgi_app_with_lifespan"):
                    create_app()

                    mock_import.assert_called_once()

    def test_import_module_not_found(self, monkeypatch):
        """Should raise RuntimeError if module not found."""
        monkeypatch.setenv("MYFY_APP_MODULE", "nonexistent_module")

        with patch("myfy_cli.asgi_factory.importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("No module named 'nonexistent_module'")

            with pytest.raises(RuntimeError, match="Failed to import module"):
                create_app()

    def test_app_var_not_found(self, monkeypatch):
        """Should raise RuntimeError if app_var not found in module."""
        monkeypatch.setenv("MYFY_APP_MODULE", "test_app")

        with patch("myfy_cli.asgi_factory.importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module

            with patch("myfy_cli.asgi_factory.getattr") as mock_getattr:
                mock_getattr.side_effect = AttributeError("'module' object has no attribute 'app'")

                with pytest.raises(RuntimeError, match="Variable 'app' not found"):
                    create_app()


class TestCreateAppValidation:
    """Test application instance validation."""

    def test_validates_application_instance(self, monkeypatch):
        """Should validate that variable is an Application instance."""
        monkeypatch.setenv("MYFY_APP_MODULE", "test_app")

        with patch("myfy_cli.asgi_factory.importlib.import_module"):
            with patch("myfy_cli.asgi_factory.getattr") as mock_getattr:
                # Return a non-Application object
                mock_getattr.return_value = "not an application"

                with pytest.raises(RuntimeError, match="not an Application instance"):
                    create_app()

    def test_accepts_valid_application(self, monkeypatch):
        """Should accept valid Application instance."""
        monkeypatch.setenv("MYFY_APP_MODULE", "test_app")

        with patch("myfy_cli.asgi_factory.importlib.import_module"):
            with patch("myfy_cli.asgi_factory.getattr") as mock_getattr:
                from myfy.core import Application

                mock_app = Mock(spec=Application)
                mock_getattr.return_value = mock_app

                with patch(
                    "myfy_cli.asgi_factory.create_asgi_app_with_lifespan"
                ) as mock_create_asgi:
                    mock_create_asgi.return_value = MagicMock()

                    asgi_app = create_app()

                    # Should call create_asgi_app_with_lifespan
                    mock_create_asgi.assert_called_once_with(mock_app)
                    assert asgi_app is not None


class TestCreateAppPathHandling:
    """Test Python path handling."""

    def test_adds_cwd_to_path(self, monkeypatch, tmp_path):
        """Should add current directory to sys.path."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("MYFY_APP_MODULE", "test_app")

        with patch("myfy_cli.asgi_factory.importlib.import_module"):
            with patch("myfy_cli.asgi_factory.getattr") as mock_getattr:
                from myfy.core import Application

                mock_app = Mock(spec=Application)
                mock_getattr.return_value = mock_app

                with patch("myfy_cli.asgi_factory.create_asgi_app_with_lifespan"):
                    with patch("myfy_cli.asgi_factory.sys") as mock_sys:
                        mock_sys.path = []

                        create_app()

                        # Should insert cwd into path
                        assert mock_sys.path.insert.called


class TestCreateAppIntegration:
    """Test full app creation workflow."""

    def test_creates_asgi_app_with_lifespan(self, monkeypatch):
        """Should create ASGI app with lifespan management."""
        monkeypatch.setenv("MYFY_APP_MODULE", "test_app")

        with patch("myfy_cli.asgi_factory.importlib.import_module"):
            with patch("myfy_cli.asgi_factory.getattr") as mock_getattr:
                from myfy.core import Application

                mock_app = Mock(spec=Application)
                mock_getattr.return_value = mock_app

                with patch(
                    "myfy_cli.asgi_factory.create_asgi_app_with_lifespan"
                ) as mock_create_asgi:
                    mock_asgi_app = MagicMock()
                    mock_create_asgi.return_value = mock_asgi_app

                    result = create_app()

                    # Should call factory with application
                    mock_create_asgi.assert_called_once_with(mock_app)

                    # Should return ASGI app
                    assert result is mock_asgi_app

    def test_error_messages_are_helpful(self, monkeypatch):
        """Should provide helpful error messages."""
        # Test missing module error
        monkeypatch.setenv("MYFY_APP_MODULE", "missing_module")

        with patch("myfy_cli.asgi_factory.importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("No module")

            with pytest.raises(RuntimeError) as exc_info:
                create_app()

            assert "Failed to import module 'missing_module'" in str(exc_info.value)
            assert "Make sure the module exists" in str(exc_info.value)
