"""
User module configuration.

Each module defines its own settings for modularity (ADR-0002).
"""

from __future__ import annotations

import secrets

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import SettingsConfigDict

from myfy.core.config import BaseSettings


class UserSettings(BaseSettings):
    """
    User module settings.

    Configure authentication, sessions, OAuth providers, and user management.

    Environment variables use the MYFY_USER_ prefix:
    - MYFY_USER_SECRET_KEY
    - MYFY_USER_SESSION_LIFETIME
    - MYFY_USER_OAUTH_GOOGLE_CLIENT_ID
    - etc.

    Example:
        ```python
        # Via environment
        export MYFY_USER_SECRET_KEY="your-secret-key"
        export MYFY_USER_OAUTH_GOOGLE_CLIENT_ID="your-client-id"

        # Via code
        settings = UserSettings(
            secret_key=SecretStr("your-secret-key"),
            require_email_verification=False,
        )
        ```
    """

    # Core security
    secret_key: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe(32)),
        description="Secret key for signing tokens and sessions. "
        "IMPORTANT: Set this in production!",
    )

    # Password settings
    password_algorithm: str = Field(
        default="argon2",
        description="Password hashing algorithm (argon2, bcrypt)",
    )
    password_min_length: int = Field(
        default=8,
        description="Minimum password length",
        ge=6,
    )
    password_require_uppercase: bool = Field(
        default=False,
        description="Require at least one uppercase letter",
    )
    password_require_lowercase: bool = Field(
        default=False,
        description="Require at least one lowercase letter",
    )
    password_require_digit: bool = Field(
        default=False,
        description="Require at least one digit",
    )
    password_require_special: bool = Field(
        default=False,
        description="Require at least one special character",
    )

    # Session settings
    session_cookie_name: str = Field(
        default="myfy_session",
        description="Name of the session cookie",
    )
    session_lifetime: int = Field(
        default=86400 * 7,  # 7 days
        description="Session lifetime in seconds",
        ge=60,
    )
    session_secure: bool = Field(
        default=True,
        description="Whether session cookie requires HTTPS",
    )
    session_httponly: bool = Field(
        default=True,
        description="Whether session cookie is HTTP-only",
    )
    session_samesite: str = Field(
        default="lax",
        description="SameSite cookie attribute (strict, lax, none)",
    )

    # JWT settings (for API tokens)
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
    )
    jwt_access_token_lifetime: int = Field(
        default=3600,  # 1 hour
        description="JWT access token lifetime in seconds",
        ge=60,
    )
    jwt_refresh_token_lifetime: int = Field(
        default=86400 * 30,  # 30 days
        description="JWT refresh token lifetime in seconds",
        ge=60,
    )

    # Email verification
    require_email_verification: bool = Field(
        default=True,
        description="Whether to require email verification before login",
    )
    email_verification_lifetime: int = Field(
        default=86400,  # 24 hours
        description="Email verification token lifetime in seconds",
        ge=60,
    )

    # Password reset
    password_reset_lifetime: int = Field(
        default=3600,  # 1 hour
        description="Password reset token lifetime in seconds",
        ge=60,
    )

    # Rate limiting
    login_rate_limit: str = Field(
        default="5/minute",
        description="Rate limit for login attempts",
    )
    register_rate_limit: str = Field(
        default="3/minute",
        description="Rate limit for registration",
    )
    password_reset_rate_limit: str = Field(
        default="3/hour",
        description="Rate limit for password reset requests",
    )

    # OAuth providers - Google
    oauth_google_client_id: str = Field(
        default="",
        description="Google OAuth client ID",
    )
    oauth_google_client_secret: SecretStr = Field(
        default_factory=lambda: SecretStr(""),
        description="Google OAuth client secret",
    )
    oauth_google_scopes: list[str] = Field(
        default=["openid", "email", "profile"],
        description="Google OAuth scopes",
    )

    # OAuth providers - GitHub
    oauth_github_client_id: str = Field(
        default="",
        description="GitHub OAuth client ID",
    )
    oauth_github_client_secret: SecretStr = Field(
        default_factory=lambda: SecretStr(""),
        description="GitHub OAuth client secret",
    )
    oauth_github_scopes: list[str] = Field(
        default=["user:email", "read:user"],
        description="GitHub OAuth scopes",
    )

    # URLs
    login_url: str = Field(
        default="/login",
        description="Login page URL",
    )
    logout_url: str = Field(
        default="/logout",
        description="Logout URL",
    )
    register_url: str = Field(
        default="/register",
        description="Registration page URL",
    )
    after_login_url: str = Field(
        default="/",
        description="Redirect URL after successful login",
    )
    after_logout_url: str = Field(
        default="/",
        description="Redirect URL after logout",
    )
    after_register_url: str = Field(
        default="/",
        description="Redirect URL after registration",
    )

    # Feature flags
    allow_registration: bool = Field(
        default=True,
        description="Whether to allow new user registrations",
    )
    allow_password_login: bool = Field(
        default=True,
        description="Whether to allow email/password login",
    )

    @field_validator("password_algorithm")
    @classmethod
    def validate_password_algorithm(cls, v: str) -> str:
        """Validate password algorithm is supported."""
        valid = ["argon2", "bcrypt"]
        if v not in valid:
            msg = f"Invalid password algorithm: {v}. Valid options: {', '.join(valid)}"
            raise ValueError(msg)
        return v

    @field_validator("session_samesite")
    @classmethod
    def validate_samesite(cls, v: str) -> str:
        """Validate SameSite attribute."""
        valid = ["strict", "lax", "none"]
        v_lower = v.lower()
        if v_lower not in valid:
            msg = f"Invalid SameSite value: {v}. Valid options: {', '.join(valid)}"
            raise ValueError(msg)
        return v_lower

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm is supported."""
        valid = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v not in valid:
            msg = f"Invalid JWT algorithm: {v}. Valid options: {', '.join(valid)}"
            raise ValueError(msg)
        return v

    def is_oauth_provider_configured(self, provider: str) -> bool:
        """Check if an OAuth provider is configured."""
        if provider == "google":
            return bool(self.oauth_google_client_id)
        if provider == "github":
            return bool(self.oauth_github_client_id)
        return False

    def get_configured_oauth_providers(self) -> list[str]:
        """Get list of configured OAuth providers."""
        providers = []
        if self.oauth_google_client_id:
            providers.append("google")
        if self.oauth_github_client_id:
            providers.append("github")
        return providers

    model_config = SettingsConfigDict(env_prefix="MYFY_USER_")
