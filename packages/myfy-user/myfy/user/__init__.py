"""
myfy-user: User management module for myfy framework.

Provides:
- Email/password authentication
- OAuth authentication (Google, GitHub)
- Session management (cookies) and JWT tokens (API)
- User profile management
- Password reset and email verification
- Bundled Jinja2 templates with DaisyUI styling

Usage:
    ```python
    from myfy.user import UserModule, UserSettings

    # Basic usage with defaults
    user_module = UserModule()

    # With OAuth providers
    user_module = UserModule(
        oauth_providers=["google", "github"],
    )

    # With custom user model
    from myfy.user import BaseUser

    class User(BaseUser):
        __tablename__ = "users"
        full_name: Mapped[str | None] = mapped_column(String(255))

    user_module = UserModule(user_model=User)

    # Integration with AuthModule
    app.add_module(DataModule())
    app.add_module(WebModule())
    app.add_module(AuthModule(
        authenticated_provider=user_module.get_authenticated_provider(),
    ))
    app.add_module(user_module)
    ```
"""

from __future__ import annotations

from myfy.user.auth.jwt import JWTService

# Auth services
from myfy.user.auth.password import PasswordHasher
from myfy.user.auth.provider import create_authenticated_provider
from myfy.user.auth.session import SessionManager

# Configuration
from myfy.user.config import UserSettings

# Errors
from myfy.user.errors import (
    EmailNotVerifiedError,
    InvalidCredentialsError,
    OAuthError,
    OAuthProviderNotConfiguredError,
    OAuthProviderNotFoundError,
    OAuthTokenExchangeError,
    OAuthUserInfoError,
    PasswordTooWeakError,
    SessionError,
    SessionExpiredError,
    SessionInvalidError,
    TokenExpiredError,
    TokenInvalidError,
    UserAlreadyExistsError,
    UserInactiveError,
    UserModuleError,
    UserNotFoundError,
)

# Extensions/Protocols
from myfy.user.extensions import IUserProvider

# Models
from myfy.user.models.base import BaseUser, DefaultUser
from myfy.user.models.oauth import OAuthConnection
from myfy.user.models.token import EmailVerificationToken, PasswordResetToken

# Module
from myfy.user.module import UserModule

# OAuth
from myfy.user.oauth.base import OAuthProvider, OAuthUserInfo
from myfy.user.oauth.github import GitHubOAuthProvider
from myfy.user.oauth.google import GoogleOAuthProvider
from myfy.user.oauth.registry import OAuthProviderRegistry
from myfy.user.services.email import EmailService

# Services
from myfy.user.services.user import UserService

# Tasks (optional - requires myfy-tasks)
from myfy.user.tasks import (
    cleanup_expired_tokens,
    cleanup_inactive_users,
    send_password_reset_email,
    send_verification_email,
    send_welcome_email,
)
from myfy.user.version import __version__

__all__ = [
    # Version
    "__version__",
    # Module
    "UserModule",
    # Configuration
    "UserSettings",
    # Extensions
    "IUserProvider",
    # Models
    "BaseUser",
    "DefaultUser",
    "OAuthConnection",
    "EmailVerificationToken",
    "PasswordResetToken",
    # Auth services
    "PasswordHasher",
    "SessionManager",
    "JWTService",
    "create_authenticated_provider",
    # OAuth
    "OAuthProvider",
    "OAuthUserInfo",
    "GoogleOAuthProvider",
    "GitHubOAuthProvider",
    "OAuthProviderRegistry",
    # Services
    "UserService",
    "EmailService",
    # Tasks
    "send_verification_email",
    "send_password_reset_email",
    "send_welcome_email",
    "cleanup_expired_tokens",
    "cleanup_inactive_users",
    # Errors
    "UserModuleError",
    "UserNotFoundError",
    "UserAlreadyExistsError",
    "InvalidCredentialsError",
    "EmailNotVerifiedError",
    "UserInactiveError",
    "TokenExpiredError",
    "TokenInvalidError",
    "PasswordTooWeakError",
    "OAuthError",
    "OAuthProviderNotFoundError",
    "OAuthProviderNotConfiguredError",
    "OAuthTokenExchangeError",
    "OAuthUserInfoError",
    "SessionError",
    "SessionExpiredError",
    "SessionInvalidError",
]


def user_module() -> UserModule:
    """
    Entry point for myfy module discovery.

    This function is registered as a myfy.modules entry point.
    """
    return UserModule()
