"""
Tests for the configuration system.

Tests profile-based settings, environment variables, and validation.
"""

import os
from pathlib import Path

import pytest
from pydantic import Field
from pydantic_settings import SettingsConfigDict

from myfy.core.config.settings import BaseSettings, CoreSettings, Profile, load_settings


class TestSettings(BaseSettings):
    """Test settings class for testing."""

    app_name: str = "test-app"
    db_url: str = "sqlite:///:memory:"
    api_key: str = "secret-key"
    debug: bool = False
    max_connections: int = 10

    model_config = SettingsConfigDict(
        env_prefix="TEST_",
        env_file=".env",
    )


class TestBaseSettings:
    """Test BaseSettings functionality."""

    def test_create_settings_with_defaults(self):
        """Should create settings with default values."""
        settings = TestSettings()

        assert settings.app_name == "test-app"
        assert settings.db_url == "sqlite:///:memory:"
        assert settings.debug is False

    def test_create_settings_with_overrides(self):
        """Should create settings with overridden values."""
        settings = TestSettings(
            app_name="custom-app",
            db_url="postgresql://localhost",
            debug=True,
        )

        assert settings.app_name == "custom-app"
        assert settings.db_url == "postgresql://localhost"
        assert settings.debug is True

    def test_model_dump_safe_redacts_secrets(self):
        """Should redact secret fields in model_dump_safe."""
        settings = TestSettings(
            api_key="super-secret-key",
            db_url="postgresql://user:password@localhost/db",
        )

        safe_dump = settings.model_dump_safe()

        assert safe_dump["api_key"] == "***REDACTED***"
        assert safe_dump["app_name"] == "test-app"
        assert safe_dump["db_url"] == "postgresql://user:password@localhost/db"

    def test_model_dump_safe_redacts_password_fields(self):
        """Should redact password-related fields."""

        class PasswordSettings(BaseSettings):
            username: str = "user"
            password: str = "secret"
            db_password: str = "dbsecret"
            api_token: str = "token123"
            private_key: str = "privatekey"

        settings = PasswordSettings()
        safe_dump = settings.model_dump_safe()

        assert safe_dump["username"] == "user"
        assert safe_dump["password"] == "***REDACTED***"
        assert safe_dump["db_password"] == "***REDACTED***"
        assert safe_dump["api_token"] == "***REDACTED***"
        assert safe_dump["private_key"] == "***REDACTED***"

    def test_settings_from_environment_variables(self, monkeypatch):
        """Should load settings from environment variables."""
        monkeypatch.setenv("TEST_APP_NAME", "env-app")
        monkeypatch.setenv("TEST_DB_URL", "postgresql://localhost")
        monkeypatch.setenv("TEST_DEBUG", "true")
        monkeypatch.setenv("TEST_MAX_CONNECTIONS", "50")

        settings = TestSettings()

        assert settings.app_name == "env-app"
        assert settings.db_url == "postgresql://localhost"
        assert settings.debug is True
        assert settings.max_connections == 50


class TestProfile:
    """Test Profile functionality."""

    def test_get_active_profile_defaults_to_dev(self, monkeypatch):
        """Should default to dev profile."""
        monkeypatch.delenv("MYFY_PROFILE", raising=False)
        Profile._current = None

        assert Profile.get_active() == Profile.DEV

    def test_get_active_profile_from_env(self, monkeypatch):
        """Should get active profile from environment."""
        monkeypatch.setenv("MYFY_PROFILE", "prod")
        Profile._current = None

        assert Profile.get_active() == Profile.PROD

    def test_set_active_profile(self):
        """Should set active profile programmatically."""
        Profile.set_active(Profile.TEST)

        assert Profile.get_active() == Profile.TEST

    def test_is_dev(self):
        """Should check if profile is dev."""
        Profile.set_active(Profile.DEV)
        assert Profile.is_dev() is True
        assert Profile.is_test() is False
        assert Profile.is_prod() is False

    def test_is_test(self):
        """Should check if profile is test."""
        Profile.set_active(Profile.TEST)
        assert Profile.is_test() is True
        assert Profile.is_dev() is False
        assert Profile.is_prod() is False

    def test_is_prod(self):
        """Should check if profile is prod."""
        Profile.set_active(Profile.PROD)
        assert Profile.is_prod() is True
        assert Profile.is_dev() is False
        assert Profile.is_test() is False


class TestCoreSettings:
    """Test CoreSettings functionality."""

    def test_create_core_settings_with_defaults(self):
        """Should create core settings with defaults."""
        Profile.set_active(Profile.TEST)  # Avoid auto-debug in dev
        settings = CoreSettings()

        assert settings.app_name == "myfy-app"
        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert settings.log_format == "json"
        assert settings.shutdown_timeout == 10.0

    def test_core_settings_auto_debug_in_dev(self):
        """Should auto-enable debug in dev profile."""
        Profile.set_active(Profile.DEV)
        settings = CoreSettings()

        assert settings.debug is True

    def test_core_settings_explicit_debug_overrides_profile(self):
        """Should allow explicit debug override."""
        Profile.set_active(Profile.DEV)
        settings = CoreSettings(debug=False)

        assert settings.debug is False

    def test_core_settings_from_environment(self, monkeypatch):
        """Should load core settings from environment."""
        monkeypatch.setenv("MYFY_APP_NAME", "my-custom-app")
        monkeypatch.setenv("MYFY_DEBUG", "true")
        monkeypatch.setenv("MYFY_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("MYFY_SHUTDOWN_TIMEOUT", "30.0")

        settings = CoreSettings()

        assert settings.app_name == "my-custom-app"
        assert settings.debug is True
        assert settings.log_level == "DEBUG"
        assert settings.shutdown_timeout == 30.0


class TestLoadSettings:
    """Test load_settings function."""

    def test_load_settings_with_default_profile(self, tmp_path, monkeypatch):
        """Should load settings with default profile."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)
        Profile.set_active(Profile.DEV)

        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_APP_NAME=base-app\nTEST_DB_URL=sqlite:///base.db\n")

        settings = load_settings(TestSettings)

        assert settings.app_name == "base-app"
        assert settings.db_url == "sqlite:///base.db"

    def test_load_settings_with_profile_override(self, tmp_path, monkeypatch):
        """Should load settings with profile-specific overrides."""
        monkeypatch.chdir(tmp_path)
        Profile.set_active(Profile.PROD)

        # Create base .env file
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_APP_NAME=base-app\nTEST_DB_URL=sqlite:///base.db\n")

        # Create profile-specific .env.prod file
        prod_env_file = tmp_path / ".env.prod"
        prod_env_file.write_text("TEST_DB_URL=postgresql://prod-db\nTEST_DEBUG=false\n")

        settings = load_settings(TestSettings)

        # Profile-specific should override base
        assert settings.app_name == "base-app"  # From .env
        assert settings.db_url == "postgresql://prod-db"  # Overridden in .env.prod

    def test_load_settings_env_vars_override_files(self, tmp_path, monkeypatch):
        """Should prioritize environment variables over .env files."""
        monkeypatch.chdir(tmp_path)
        Profile.set_active(Profile.DEV)

        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_APP_NAME=file-app\n")

        # Set environment variable
        monkeypatch.setenv("TEST_APP_NAME", "env-app")

        settings = load_settings(TestSettings)

        # Environment variable should win
        assert settings.app_name == "env-app"

    def test_load_settings_with_custom_profile(self, tmp_path, monkeypatch):
        """Should load settings with custom profile."""
        monkeypatch.chdir(tmp_path)

        # Create .env.custom file
        custom_env = tmp_path / ".env.custom"
        custom_env.write_text("TEST_APP_NAME=custom-app\n")

        settings = load_settings(TestSettings, profile="custom")

        assert settings.app_name == "custom-app"

    def test_load_settings_missing_profile_file_uses_defaults(self, tmp_path, monkeypatch):
        """Should use defaults when profile-specific file doesn't exist."""
        monkeypatch.chdir(tmp_path)
        Profile.set_active(Profile.PROD)

        # No .env.prod file exists
        settings = load_settings(TestSettings)

        # Should use class defaults
        assert settings.app_name == "test-app"
        assert settings.db_url == "sqlite:///:memory:"

    def test_load_settings_with_custom_env_file(self, tmp_path, monkeypatch):
        """Should load settings from custom env file."""
        monkeypatch.chdir(tmp_path)

        # Create custom env file
        custom_env = tmp_path / "custom.env"
        custom_env.write_text("TEST_APP_NAME=custom-file-app\n")

        settings = load_settings(TestSettings, env_file=custom_env)

        assert settings.app_name == "custom-file-app"


class TestSettingsValidation:
    """Test settings validation with Pydantic."""

    def test_settings_validates_types(self):
        """Should validate setting types."""

        class StrictSettings(BaseSettings):
            port: int = 8000
            enabled: bool = True

        # Valid values
        settings = StrictSettings(port=9000, enabled=False)
        assert settings.port == 9000
        assert settings.enabled is False

        # Pydantic will coerce string to int
        settings2 = StrictSettings(port="8080")
        assert settings2.port == 8080

    def test_settings_validates_required_fields(self):
        """Should validate required fields."""

        class RequiredSettings(BaseSettings):
            api_key: str
            db_url: str = "default"

        # Missing required field should raise
        with pytest.raises(Exception):  # Pydantic ValidationError
            RequiredSettings()

        # With required field should work
        settings = RequiredSettings(api_key="key123")
        assert settings.api_key == "key123"
        assert settings.db_url == "default"

    def test_settings_with_field_validators(self):
        """Should use Field validators."""

        class ValidatedSettings(BaseSettings):
            port: int = Field(default=8000, ge=1, le=65535)
            app_name: str = Field(default="app", min_length=1, max_length=50)

        # Valid values
        settings = ValidatedSettings(port=8080, app_name="myapp")
        assert settings.port == 8080

        # Invalid port (out of range) should raise
        with pytest.raises(Exception):  # Pydantic ValidationError
            ValidatedSettings(port=70000)

        # Invalid app_name (too long) should raise
        with pytest.raises(Exception):  # Pydantic ValidationError
            ValidatedSettings(app_name="a" * 100)
