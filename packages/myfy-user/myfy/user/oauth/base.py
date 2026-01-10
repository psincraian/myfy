"""
Base OAuth provider protocol and implementation.
"""

from __future__ import annotations

import urllib.parse
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import httpx

from myfy.user.errors import OAuthTokenExchangeError, OAuthUserInfoError


@dataclass
class OAuthUserInfo:
    """
    User information from OAuth provider.

    Contains standardized user data extracted from provider responses.
    """

    provider_user_id: str
    email: str | None
    name: str | None
    avatar_url: str | None
    raw_data: dict[str, Any]


@runtime_checkable
class OAuthProvider(Protocol):
    """
    Protocol for OAuth providers.

    Implement this protocol to add new OAuth providers.
    """

    @property
    def name(self) -> str:
        """Provider name (e.g., 'google', 'github')."""
        ...

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """
        Get URL to redirect user for authorization.

        Args:
            state: Random state for CSRF protection
            redirect_uri: URL to redirect back to after authorization

        Returns:
            Authorization URL
        """
        ...

    async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect URI used in authorization

        Returns:
            Token response dict with access_token, etc.
        """
        ...

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """
        Get user information from provider.

        Args:
            access_token: OAuth access token

        Returns:
            OAuthUserInfo with user data
        """
        ...


class BaseOAuthProvider(ABC):
    """
    Base class for OAuth providers.

    Provides common functionality for OAuth 2.0 providers.

    Example:
        ```python
        class MyProvider(BaseOAuthProvider):
            @property
            def name(self) -> str:
                return "myprovider"

            @property
            def authorization_endpoint(self) -> str:
                return "https://myprovider.com/oauth/authorize"

            @property
            def token_endpoint(self) -> str:
                return "https://myprovider.com/oauth/token"

            @property
            def userinfo_endpoint(self) -> str:
                return "https://myprovider.com/api/user"

            async def get_user_info(self, access_token: str) -> OAuthUserInfo:
                # Implement provider-specific user info parsing
                ...
        ```
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        scopes: list[str] | None = None,
    ) -> None:
        """
        Initialize OAuth provider.

        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            scopes: OAuth scopes to request
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._scopes = scopes or []

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        ...

    @property
    @abstractmethod
    def authorization_endpoint(self) -> str:
        """OAuth authorization endpoint URL."""
        ...

    @property
    @abstractmethod
    def token_endpoint(self) -> str:
        """OAuth token endpoint URL."""
        ...

    @property
    @abstractmethod
    def userinfo_endpoint(self) -> str:
        """User info API endpoint URL."""
        ...

    def get_authorization_url(
        self,
        state: str,
        redirect_uri: str,
        extra_params: dict[str, str] | None = None,
    ) -> str:
        """
        Build authorization URL.

        Args:
            state: Random state for CSRF protection
            redirect_uri: URL to redirect back to
            extra_params: Additional query parameters

        Returns:
            Authorization URL
        """
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self._scopes),
            "state": state,
        }

        if extra_params:
            params.update(extra_params)

        query = urllib.parse.urlencode(params)
        return f"{self.authorization_endpoint}?{query}"

    async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code
            redirect_uri: Same redirect URI used in authorization

        Returns:
            Token response dict

        Raises:
            OAuthTokenExchangeError: If token exchange fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.token_endpoint,
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code",
                    },
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise OAuthTokenExchangeError(
                    self.name,
                    f"HTTP {e.response.status_code}: {e.response.text}",
                ) from e
            except httpx.RequestError as e:
                raise OAuthTokenExchangeError(
                    self.name,
                    f"Request failed: {e!s}",
                ) from e

    @abstractmethod
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user info from provider."""
        ...

    async def _fetch_user_info(
        self,
        access_token: str,
        url: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch user info from API.

        Args:
            access_token: OAuth access token
            url: Optional custom URL (defaults to userinfo_endpoint)

        Returns:
            Raw user info dict

        Raises:
            OAuthUserInfoError: If request fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url or self.userinfo_endpoint,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise OAuthUserInfoError(
                    self.name,
                    f"HTTP {e.response.status_code}: {e.response.text}",
                ) from e
            except httpx.RequestError as e:
                raise OAuthUserInfoError(
                    self.name,
                    f"Request failed: {e!s}",
                ) from e
