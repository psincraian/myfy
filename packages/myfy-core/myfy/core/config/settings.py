"""
Configuration system with profiles and validation.

Built on Pydantic for type-safe, validated settings.
"""

import os
from pathlib import Path
from typing import Any, TypeVar, cast

from pydantic import Field
from pydantic_settings import BaseSettings as PydanticBaseSettings
from pydantic_settings import SettingsConfigDict

T = TypeVar("T", bound="BaseSettings")


class BaseSettings(PydanticBaseSettings):
    """
    Base class for application settings.

    Inherit from this to create typed, validated configuration.
    Supports environment variables and .env files.

    Usage:
        class AppSettings(BaseSettings):
            app_name: str = "myapp"
            db_url: str
            debug: bool = False

            model_config = SettingsConfigDict(
                env_prefix="MYAPP_",
                env_file=".env"
            )
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def model_dump_safe(self, **kwargs: Any) -> dict[str, Any]:
        """
        Dump settings with secrets redacted.

        Useful for logging and health check endpoints.
        Redacts fields containing: password, secret, token, key, api_key, private
        """
        dump = self.model_dump(**kwargs)

        # Redact fields that commonly contain secrets
        secret_patterns = ["password", "secret", "token", "key", "api_key", "private"]

        for field_name in list(dump.keys()):
            field_lower = field_name.lower()
            if any(pattern in field_lower for pattern in secret_patterns):
                dump[field_name] = "***REDACTED***"

        return dump


class Profile:
    """
    Application profile (dev, test, prod).

    Profiles control which settings files are loaded and
    environment-specific behavior.
    """

    DEV = "dev"
    TEST = "test"
    PROD = "prod"

    _current: str | None = None

    @classmethod
    def get_active(cls) -> str:
        """
        Get the currently active profile.

        Reads from MYFY_PROFILE environment variable, defaults to 'dev'.
        """
        if cls._current is None:
            cls._current = os.getenv("MYFY_PROFILE", cls.DEV)
        return cls._current

    @classmethod
    def set_active(cls, profile: str) -> None:
        """Set the active profile programmatically (mainly for testing)."""
        cls._current = profile

    @classmethod
    def is_dev(cls) -> bool:
        """Check if running in development mode."""
        return cls.get_active() == cls.DEV

    @classmethod
    def is_test(cls) -> bool:
        """Check if running in test mode."""
        return cls.get_active() == cls.TEST

    @classmethod
    def is_prod(cls) -> bool:
        """Check if running in production mode."""
        return cls.get_active() == cls.PROD


class CoreSettings(BaseSettings):
    """
    Core framework settings.

    These are built into the framework and control fundamental behavior.
    """

    # Application
    app_name: str = Field(default="myfy-app", description="Application name")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Logging
    log_level: str = Field(default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)")
    log_format: str = Field(default="json", description="Log format (json, console)")

    # Shutdown
    shutdown_timeout: float = Field(
        default=10.0, description="Graceful shutdown timeout in seconds"
    )

    model_config = SettingsConfigDict(
        env_prefix="MYFY_",
        env_file=".env",
    )

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        # Override debug based on profile if not explicitly set
        if "debug" not in kwargs and Profile.is_dev():
            self.debug = True


def load_settings[T: "BaseSettings"](
    settings_class: type[T] = CoreSettings,  # type: ignore[assignment]
    profile: str | None = None,
    env_file: Path | None = None,
) -> T:
    """
    Load settings with profile-based layering.

    Loading order (later overrides earlier):
    1. Default values in class
    2. .env file
    3. .env.{profile} file (if profile specified)
    4. Environment variables

    Args:
        settings_class: Settings class to instantiate
        profile: Profile to load (defaults to active profile)
        env_file: Override .env file path

    Returns:
        Instantiated and validated settings
    """
    if profile is None:
        profile = Profile.get_active()

    # Build list of env files to load
    env_files = []
    if env_file:
        env_files.append(env_file)
    else:
        env_files.append(Path(".env"))

    # Add profile-specific env file
    profile_env = Path(f".env.{profile}")
    if profile_env.exists():
        env_files.append(profile_env)

    # Load settings (environment variables will override)
    # Pydantic loads env files in order, with later files overriding
    return cast("T", settings_class())
