"""Application configuration settings."""

from typing import ClassVar

from pydantic import Field

from myfy.core import BaseSettings
from myfy.frontend.config import FrontendSettings
from myfy.web.config import WebSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings.

    Environment variables:
        DATABASE_URL: Database connection URL
        DATABASE_ECHO: Enable SQL query logging
        DATABASE_POOL_SIZE: Connection pool size
        DATABASE_MAX_OVERFLOW: Maximum overflow connections
    """

    model_config: ClassVar[dict] = {"env_prefix": "DATABASE_"}

    url: str = "postgresql+asyncpg://myfy:myfy_dev@localhost:5432/myfy_db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_recycle: int = 3600  # Recycle connections every hour
    pool_timeout: int = 30  # Wait 30s for connection


class SecuritySettings(BaseSettings):
    """Security configuration settings.

    Environment variables:
        SECURITY_SECRET_KEY: Secret key for CSRF and sessions (REQUIRED)
        SECURITY_CSRF_MAX_AGE: CSRF token max age in seconds
        SECURITY_RATE_LIMIT: Rate limit string (e.g., "5/minute")
        SECURITY_HTTPS_ONLY: Enable HTTPS-only cookies
        SECURITY_ALLOWED_HOSTS: Comma-separated list of allowed hosts
    """

    model_config: ClassVar[dict] = {"env_prefix": "SECURITY_"}

    secret_key: str  # Required, no default
    csrf_max_age: int = 3600  # 1 hour
    rate_limit: str = "5/minute"
    https_only: bool = False
    allowed_hosts: str = "localhost,127.0.0.1"


class AppSettings(BaseSettings):
    """Main application settings.

    This class aggregates all configuration for the application including
    nested module settings. All nested settings are automatically registered
    in the DI container (ADR-0007: Optional Nested Module Settings).

    Environment variables:
        APP_NAME: Application name
        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """

    app_name: str = "myfy Website"
    log_level: str = "INFO"

    # Nested module settings (auto-registered in DI container)
    web: WebSettings = Field(default_factory=WebSettings)
    frontend: FrontendSettings = Field(default_factory=FrontendSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
