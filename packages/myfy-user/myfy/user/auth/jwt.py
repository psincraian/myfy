"""
JWT token service for API authentication.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import jwt

from myfy.user.errors import TokenExpiredError, TokenInvalidError

if TYPE_CHECKING:
    from myfy.user.config import UserSettings


class JWTService:
    """
    JWT token service for API authentication.

    Provides access tokens and refresh tokens for stateless authentication.

    Usage:
        ```python
        jwt_service = JWTService(settings)

        # Create tokens
        access_token = jwt_service.create_access_token(user_id="123")
        refresh_token = jwt_service.create_refresh_token(user_id="123")

        # Decode and verify
        payload = jwt_service.decode_access_token(access_token)
        user_id = payload["sub"]
        ```
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_lifetime: int = 3600,  # 1 hour
        refresh_token_lifetime: int = 2592000,  # 30 days
        issuer: str = "myfy",
    ) -> None:
        """
        Initialize JWT service.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT signing algorithm
            access_token_lifetime: Access token lifetime in seconds
            refresh_token_lifetime: Refresh token lifetime in seconds
            issuer: Token issuer claim
        """
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_token_lifetime = access_token_lifetime
        self._refresh_token_lifetime = refresh_token_lifetime
        self._issuer = issuer

    @classmethod
    def from_settings(cls, settings: UserSettings) -> JWTService:
        """Create JWT service from UserSettings."""
        return cls(
            secret_key=settings.secret_key.get_secret_value(),
            algorithm=settings.jwt_algorithm,
            access_token_lifetime=settings.jwt_access_token_lifetime,
            refresh_token_lifetime=settings.jwt_refresh_token_lifetime,
        )

    def create_access_token(
        self,
        user_id: str,
        additional_claims: dict[str, Any] | None = None,
    ) -> str:
        """
        Create an access token.

        Args:
            user_id: User ID to encode in token
            additional_claims: Additional claims to include

        Returns:
            Encoded JWT token string
        """
        now = datetime.now(UTC)
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(seconds=self._access_token_lifetime),
            "iss": self._issuer,
            "type": "access",
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(
        self,
        user_id: str,
        additional_claims: dict[str, Any] | None = None,
    ) -> str:
        """
        Create a refresh token.

        Args:
            user_id: User ID to encode in token
            additional_claims: Additional claims to include

        Returns:
            Encoded JWT token string
        """
        now = datetime.now(UTC)
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(seconds=self._refresh_token_lifetime),
            "iss": self._issuer,
            "type": "refresh",
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> dict[str, Any]:
        """
        Decode and verify an access token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            TokenExpiredError: If token is expired
            TokenInvalidError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                issuer=self._issuer,
            )

            # Verify it's an access token
            if payload.get("type") != "access":
                raise TokenInvalidError("access")

            return payload

        except jwt.ExpiredSignatureError as e:
            raise TokenExpiredError("access") from e
        except jwt.InvalidTokenError as e:
            raise TokenInvalidError("access") from e

    def decode_refresh_token(self, token: str) -> dict[str, Any]:
        """
        Decode and verify a refresh token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            TokenExpiredError: If token is expired
            TokenInvalidError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                issuer=self._issuer,
            )

            # Verify it's a refresh token
            if payload.get("type") != "refresh":
                raise TokenInvalidError("refresh")

            return payload

        except jwt.ExpiredSignatureError as e:
            raise TokenExpiredError("refresh") from e
        except jwt.InvalidTokenError as e:
            raise TokenInvalidError("refresh") from e

    def decode_token_safe(self, token: str) -> dict[str, Any] | None:
        """
        Decode token without raising exceptions.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload or None if invalid
        """
        try:
            return jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                issuer=self._issuer,
            )
        except jwt.InvalidTokenError:
            return None

    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Create a new access token from a refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token

        Raises:
            TokenExpiredError: If refresh token is expired
            TokenInvalidError: If refresh token is invalid
        """
        payload = self.decode_refresh_token(refresh_token)
        return self.create_access_token(payload["sub"])
