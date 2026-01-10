"""Custom exceptions for myfy-user module."""

from __future__ import annotations


class UserModuleError(Exception):
    """Base exception for user module errors."""


class UserNotFoundError(UserModuleError):
    """User not found."""

    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        super().__init__(f"User not found: {identifier}")


class UserAlreadyExistsError(UserModuleError):
    """User with this email already exists."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"User already exists: {email}")


class InvalidCredentialsError(UserModuleError):
    """Invalid email or password."""

    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class EmailNotVerifiedError(UserModuleError):
    """Email not verified."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"Email not verified: {email}")


class UserInactiveError(UserModuleError):
    """User account is inactive."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"User account is inactive: {email}")


class TokenExpiredError(UserModuleError):
    """Token has expired."""

    def __init__(self, token_type: str) -> None:
        self.token_type = token_type
        super().__init__(f"{token_type} token has expired")


class TokenInvalidError(UserModuleError):
    """Token is invalid."""

    def __init__(self, token_type: str) -> None:
        self.token_type = token_type
        super().__init__(f"Invalid {token_type} token")


class PasswordTooWeakError(UserModuleError):
    """Password does not meet requirements."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Password too weak: {reason}")


class OAuthError(UserModuleError):
    """OAuth authentication error."""


class OAuthProviderNotFoundError(OAuthError):
    """OAuth provider not found."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(f"OAuth provider not found: {provider}")


class OAuthProviderNotConfiguredError(OAuthError):
    """OAuth provider not configured."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(f"OAuth provider not configured: {provider}")


class OAuthTokenExchangeError(OAuthError):
    """Failed to exchange OAuth code for tokens."""

    def __init__(self, provider: str, reason: str) -> None:
        self.provider = provider
        self.reason = reason
        super().__init__(f"OAuth token exchange failed for {provider}: {reason}")


class OAuthUserInfoError(OAuthError):
    """Failed to get user info from OAuth provider."""

    def __init__(self, provider: str, reason: str) -> None:
        self.provider = provider
        self.reason = reason
        super().__init__(f"Failed to get user info from {provider}: {reason}")


class SessionError(UserModuleError):
    """Session error."""


class SessionExpiredError(SessionError):
    """Session has expired."""

    def __init__(self) -> None:
        super().__init__("Session has expired")


class SessionInvalidError(SessionError):
    """Session is invalid."""

    def __init__(self) -> None:
        super().__init__("Invalid session")
