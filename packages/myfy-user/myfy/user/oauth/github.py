"""
GitHub OAuth provider implementation.
"""

from __future__ import annotations

import httpx

from .base import BaseOAuthProvider, OAuthUserInfo


class GitHubOAuthProvider(BaseOAuthProvider):
    """
    GitHub OAuth 2.0 provider.

    Supports authentication via GitHub accounts.

    Usage:
        ```python
        provider = GitHubOAuthProvider(
            client_id="your-client-id",
            client_secret="your-client-secret",
        )

        # Get authorization URL
        url = provider.get_authorization_url(
            state="random-state",
            redirect_uri="https://myapp.com/oauth/github/callback",
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
        Initialize GitHub OAuth provider.

        Args:
            client_id: GitHub OAuth client ID
            client_secret: GitHub OAuth client secret
            scopes: OAuth scopes (defaults to user:email, read:user)
        """
        default_scopes = ["user:email", "read:user"]
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes or default_scopes,
        )

    @property
    def name(self) -> str:
        """Provider name."""
        return "github"

    @property
    def authorization_endpoint(self) -> str:
        """GitHub authorization endpoint."""
        return "https://github.com/login/oauth/authorize"

    @property
    def token_endpoint(self) -> str:
        """GitHub token endpoint."""
        return "https://github.com/login/oauth/access_token"

    @property
    def userinfo_endpoint(self) -> str:
        """GitHub user API endpoint."""
        return "https://api.github.com/user"

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """
        Get user info from GitHub.

        GitHub requires a separate API call to get primary email.

        Args:
            access_token: GitHub access token

        Returns:
            OAuthUserInfo with GitHub user data
        """
        # Get basic user info
        data = await self._fetch_user_info(access_token)

        # Get primary email (GitHub requires separate API call)
        email = data.get("email")
        if not email:
            email = await self._get_primary_email(access_token)

        return OAuthUserInfo(
            provider_user_id=str(data["id"]),
            email=email,
            name=data.get("name") or data.get("login"),
            avatar_url=data.get("avatar_url"),
            raw_data=data,
        )

    async def _get_primary_email(self, access_token: str) -> str | None:
        """
        Get user's primary email from GitHub.

        GitHub accounts can have the email hidden, so we need to call
        the emails API to get the primary verified email.

        Args:
            access_token: GitHub access token

        Returns:
            Primary email or None if not available
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                emails = response.json()

                # Find primary verified email
                for email_data in emails:
                    if email_data.get("primary") and email_data.get("verified"):
                        return email_data.get("email")

                # Fall back to any verified email
                for email_data in emails:
                    if email_data.get("verified"):
                        return email_data.get("email")

                return None

        except (httpx.HTTPStatusError, httpx.RequestError):
            # If we can't get emails, return None
            return None
