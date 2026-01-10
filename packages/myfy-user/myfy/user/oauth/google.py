"""
Google OAuth provider implementation.
"""

from __future__ import annotations

from .base import BaseOAuthProvider, OAuthUserInfo


class GoogleOAuthProvider(BaseOAuthProvider):
    """
    Google OAuth 2.0 provider.

    Supports authentication via Google accounts.

    Usage:
        ```python
        provider = GoogleOAuthProvider(
            client_id="your-client-id",
            client_secret="your-client-secret",
        )

        # Get authorization URL
        url = provider.get_authorization_url(
            state="random-state",
            redirect_uri="https://myapp.com/oauth/google/callback",
        )

        # After callback, exchange code for tokens
        tokens = await provider.exchange_code(code, redirect_uri)

        # Get user info
        user_info = await provider.get_user_info(tokens["access_token"])
        ```
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        scopes: list[str] | None = None,
    ) -> None:
        """
        Initialize Google OAuth provider.

        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            scopes: OAuth scopes (defaults to openid, email, profile)
        """
        default_scopes = ["openid", "email", "profile"]
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes or default_scopes,
        )

    @property
    def name(self) -> str:
        """Provider name."""
        return "google"

    @property
    def authorization_endpoint(self) -> str:
        """Google authorization endpoint."""
        return "https://accounts.google.com/o/oauth2/v2/auth"

    @property
    def token_endpoint(self) -> str:
        """Google token endpoint."""
        return "https://oauth2.googleapis.com/token"

    @property
    def userinfo_endpoint(self) -> str:
        """Google user info endpoint."""
        return "https://www.googleapis.com/oauth2/v2/userinfo"

    def get_authorization_url(
        self,
        state: str,
        redirect_uri: str,
        extra_params: dict[str, str] | None = None,
    ) -> str:
        """
        Get Google authorization URL.

        Adds Google-specific parameters like access_type=offline for refresh tokens.
        """
        params = extra_params or {}
        params.setdefault("access_type", "offline")
        params.setdefault("prompt", "consent")
        return super().get_authorization_url(state, redirect_uri, params)

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """
        Get user info from Google.

        Args:
            access_token: Google access token

        Returns:
            OAuthUserInfo with Google user data
        """
        data = await self._fetch_user_info(access_token)

        return OAuthUserInfo(
            provider_user_id=data["id"],
            email=data.get("email"),
            name=data.get("name"),
            avatar_url=data.get("picture"),
            raw_data=data,
        )
