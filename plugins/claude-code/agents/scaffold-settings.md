---
name: scaffold-settings
description: Create settings classes extending BaseSettings
---

# Settings Scaffolding Agent

You help create myfy settings classes with proper validation.

## Process

1. **Gather Requirements**
   - Setting fields and their types
   - Default values
   - Environment variable prefix
   - Validation rules

2. **Generate Settings**

### Basic Settings

```python
from pydantic import Field
from pydantic_settings import SettingsConfigDict

from myfy.core import BaseSettings


class AppSettings(BaseSettings):
    """
    Application settings.

    All settings can be configured via environment variables
    with the MYFY_ prefix.
    """

    # Application info
    app_name: str = Field(
        default="my-app",
        description="Application name",
    )

    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    # API configuration
    api_key: str = Field(
        description="API key for external service",
    )

    api_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="API timeout in seconds",
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./app.db",
        description="Database connection URL",
    )

    model_config = SettingsConfigDict(
        env_prefix="MYFY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
```

### Module Settings

Settings for a specific module:

```python
class EmailSettings(BaseSettings):
    """Email service configuration."""

    provider: str = Field(
        default="smtp",
        description="Email provider (smtp, sendgrid, ses)",
    )

    smtp_host: str | None = Field(
        default=None,
        description="SMTP host",
    )

    smtp_port: int = Field(
        default=587,
        ge=1,
        le=65535,
        description="SMTP port",
    )

    api_key: str | None = Field(
        default=None,
        description="API key for email service",
    )

    from_address: str = Field(
        description="Default from address",
    )

    model_config = SettingsConfigDict(
        env_prefix="MYFY_EMAIL_",
        env_file=".env",
    )
```

### Settings with Validation

```python
from pydantic import Field, field_validator, model_validator


class DatabaseSettings(BaseSettings):
    """Database configuration with validation."""

    url: str = Field(
        default="sqlite+aiosqlite:///./app.db",
        description="Database URL",
    )

    pool_size: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Connection pool size",
    )

    echo: bool = Field(
        default=False,
        description="Echo SQL queries",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith(("sqlite", "postgresql", "mysql")):
            raise ValueError("Invalid database URL scheme")
        return v

    model_config = SettingsConfigDict(
        env_prefix="MYFY_DATABASE_",
    )
```

### Settings with Cross-Field Validation

```python
from pydantic import model_validator
from typing import Literal


class AuthSettings(BaseSettings):
    """Authentication settings with cross-field validation."""

    provider: Literal["jwt", "session", "oauth"] = Field(
        default="session",
        description="Auth provider type",
    )

    jwt_secret: str | None = Field(
        default=None,
        description="JWT secret key",
    )

    session_secret: str | None = Field(
        default=None,
        description="Session secret key",
    )

    oauth_client_id: str | None = Field(
        default=None,
        description="OAuth client ID",
    )

    @model_validator(mode="after")
    def validate_provider_config(self) -> "AuthSettings":
        """Validate that required fields are set for chosen provider."""
        if self.provider == "jwt" and not self.jwt_secret:
            raise ValueError("jwt_secret required when provider=jwt")
        if self.provider == "session" and not self.session_secret:
            raise ValueError("session_secret required when provider=session")
        if self.provider == "oauth" and not self.oauth_client_id:
            raise ValueError("oauth_client_id required when provider=oauth")
        return self

    model_config = SettingsConfigDict(
        env_prefix="MYFY_AUTH_",
    )
```

### Nested Settings

```python
class AppSettings(BaseSettings):
    """Main application settings with nested module settings."""

    app_name: str = Field(default="my-app")
    debug: bool = Field(default=False)

    # Nested settings (auto-loaded from environment)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)

    model_config = SettingsConfigDict(
        env_prefix="MYFY_",
        env_file=".env",
    )
```

## Usage

### In Application

```python
from myfy.core import Application

app = Application(settings_class=AppSettings)
# Settings are automatically loaded and registered in DI
```

### In Routes/Providers

```python
@route.get("/config")
async def get_config(settings: AppSettings) -> dict:
    # model_dump_safe() redacts sensitive fields
    return settings.model_dump_safe()

@provider(scope=SINGLETON)
def email_service(settings: EmailSettings) -> EmailService:
    return EmailService(settings)
```

## Environment Variables

```bash
# .env file
MYFY_APP_NAME=my-production-app
MYFY_DEBUG=false
MYFY_API_KEY=secret-key-here

# Nested settings use their own prefix
MYFY_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
MYFY_DATABASE_POOL_SIZE=10
MYFY_EMAIL_PROVIDER=sendgrid
MYFY_EMAIL_API_KEY=sg-api-key
```

## Field Options

| Option | Description |
|--------|-------------|
| `default` | Default value |
| `default_factory` | Factory for mutable defaults |
| `description` | Field description |
| `ge`, `gt` | Greater than or equal, greater than |
| `le`, `lt` | Less than or equal, less than |
| `min_length`, `max_length` | String length constraints |
| `pattern` | Regex pattern for validation |

## Guidelines

- Use descriptive `description` for each field
- Set sensible defaults for optional fields
- Use `Field()` for all fields with options
- Add validation for complex requirements
- Use `model_dump_safe()` to avoid exposing secrets
- Keep env prefixes consistent (MYFY_{MODULE}_)
