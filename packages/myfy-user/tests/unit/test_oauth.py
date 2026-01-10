"""Unit tests for OAuth providers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from myfy.user.errors import (
    OAuthProviderNotConfiguredError,
    OAuthProviderNotFoundError,
    OAuthTokenExchangeError,
    OAuthUserInfoError,
)
from myfy.user.oauth.base import OAuthUserInfo
from myfy.user.oauth.github import GitHubOAuthProvider
from myfy.user.oauth.google import GoogleOAuthProvider
from myfy.user.oauth.registry import OAuthProviderRegistry


class TestGoogleOAuthProvider:
    """Tests for GoogleOAuthProvider."""

    @pytest.fixture
    def google_provider(self):
        """Create Google OAuth provider."""
        return GoogleOAuthProvider(
            client_id="google-client-id",
            client_secret="google-client-secret",
            scopes=["openid", "email", "profile"],
        )

    def test_provider_name(self, google_provider):
        """Test provider name."""
        assert google_provider.name == "google"

    def test_get_authorization_url(self, google_provider):
        """Test generating authorization URL."""
        state = "random-state-123"
        redirect_uri = "https://example.com/callback"

        url = google_provider.get_authorization_url(state, redirect_uri)

        assert "accounts.google.com" in url
        assert "client_id=google-client-id" in url
        assert f"state={state}" in url
        assert "redirect_uri=" in url
        assert "scope=" in url

    def test_authorization_url_includes_scopes(self, google_provider):
        """Test authorization URL includes scopes."""
        url = google_provider.get_authorization_url("state", "https://example.com/callback")

        assert "openid" in url
        assert "email" in url
        assert "profile" in url

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, google_provider):
        """Test exchanging code for tokens."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "google-access-token",
            "refresh_token": "google-refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            tokens = await google_provider.exchange_code(
                code="auth-code",
                redirect_uri="https://example.com/callback",
            )

        assert tokens["access_token"] == "google-access-token"

    @pytest.mark.asyncio
    async def test_exchange_code_failure(self, google_provider):
        """Test exchange code failure raises error."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid code"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(OAuthTokenExchangeError):
                await google_provider.exchange_code(
                    code="invalid-code",
                    redirect_uri="https://example.com/callback",
                )

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, google_provider):
        """Test getting user info from Google."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "google-user-123",
            "email": "user@gmail.com",
            "verified_email": True,
            "name": "John Doe",
            "picture": "https://example.com/photo.jpg",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            user_info = await google_provider.get_user_info("access-token")

        assert isinstance(user_info, OAuthUserInfo)
        assert user_info.provider_user_id == "google-user-123"
        assert user_info.email == "user@gmail.com"
        assert user_info.name == "John Doe"
        assert user_info.avatar_url == "https://example.com/photo.jpg"

    @pytest.mark.asyncio
    async def test_get_user_info_failure(self, google_provider):
        """Test getting user info failure raises error."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(OAuthUserInfoError):
                await google_provider.get_user_info("invalid-token")


class TestGitHubOAuthProvider:
    """Tests for GitHubOAuthProvider."""

    @pytest.fixture
    def github_provider(self):
        """Create GitHub OAuth provider."""
        return GitHubOAuthProvider(
            client_id="github-client-id",
            client_secret="github-client-secret",
            scopes=["user:email"],
        )

    def test_provider_name(self, github_provider):
        """Test provider name."""
        assert github_provider.name == "github"

    def test_get_authorization_url(self, github_provider):
        """Test generating authorization URL."""
        state = "random-state-456"
        redirect_uri = "https://example.com/github/callback"

        url = github_provider.get_authorization_url(state, redirect_uri)

        assert "github.com" in url
        assert "client_id=github-client-id" in url
        assert f"state={state}" in url

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, github_provider):
        """Test exchanging code for tokens."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "github-access-token",
            "token_type": "bearer",
            "scope": "user:email",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            tokens = await github_provider.exchange_code(
                code="auth-code",
                redirect_uri="https://example.com/callback",
            )

        assert tokens["access_token"] == "github-access-token"

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, github_provider):
        """Test getting user info from GitHub."""
        # Mock user endpoint
        user_response = MagicMock()
        user_response.status_code = 200
        user_response.json.return_value = {
            "id": 123456,
            "login": "githubuser",
            "name": "GitHub User",
            "avatar_url": "https://github.com/avatar.jpg",
            "email": "user@github.com",
        }
        user_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = user_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            user_info = await github_provider.get_user_info("access-token")

        assert isinstance(user_info, OAuthUserInfo)
        assert user_info.provider_user_id == "123456"
        assert user_info.email == "user@github.com"
        assert user_info.name == "GitHub User"


class TestOAuthProviderRegistry:
    """Tests for OAuthProviderRegistry."""

    def test_register_google_provider(self, user_settings):
        """Test registering Google provider."""
        registry = OAuthProviderRegistry(user_settings)
        registry.register_provider("google")

        assert registry.has_provider("google") is True

    def test_register_github_provider(self, user_settings):
        """Test registering GitHub provider."""
        registry = OAuthProviderRegistry(user_settings)
        registry.register_provider("github")

        assert registry.has_provider("github") is True

    def test_register_unknown_provider_raises(self, user_settings):
        """Test registering unknown provider raises error."""
        registry = OAuthProviderRegistry(user_settings)

        with pytest.raises(OAuthProviderNotFoundError):
            registry.register_provider("unknown")

    def test_register_unconfigured_provider_raises(self):
        """Test registering provider without config raises error."""
        from myfy.user.config import UserSettings

        # Create settings without OAuth config
        settings = UserSettings(
            secret_key="test-secret-key-32-characters-long",
            oauth_google_client_id="",  # Empty = not configured
            oauth_google_client_secret="",
        )

        registry = OAuthProviderRegistry(settings)

        with pytest.raises(OAuthProviderNotConfiguredError):
            registry.register_provider("google")

    def test_get_provider(self, oauth_registry):
        """Test getting a registered provider."""
        provider = oauth_registry.get_provider("google")

        assert provider is not None
        assert provider.name == "google"

    def test_get_unregistered_provider_raises(self, user_settings):
        """Test getting unregistered provider raises error."""
        registry = OAuthProviderRegistry(user_settings)

        with pytest.raises(OAuthProviderNotFoundError):
            registry.get_provider("google")

    def test_list_providers(self, oauth_registry):
        """Test listing registered providers."""
        providers = oauth_registry.list_providers()

        assert "google" in providers
        assert "github" in providers

    def test_list_available_providers(self, user_settings):
        """Test listing available provider types."""
        registry = OAuthProviderRegistry(user_settings)
        available = registry.list_available_providers()

        assert "google" in available
        assert "github" in available

    def test_has_provider(self, oauth_registry):
        """Test checking if provider is registered."""
        assert oauth_registry.has_provider("google") is True
        assert oauth_registry.has_provider("facebook") is False


class TestOAuthUserInfo:
    """Tests for OAuthUserInfo dataclass."""

    def test_create_user_info(self):
        """Test creating OAuthUserInfo."""
        info = OAuthUserInfo(
            provider_user_id="user-123",
            email="user@example.com",
            name="Test User",
            avatar_url="https://example.com/avatar.jpg",
            raw_data={"extra": "data"},
        )

        assert info.provider_user_id == "user-123"
        assert info.email == "user@example.com"
        assert info.name == "Test User"
        assert info.avatar_url == "https://example.com/avatar.jpg"
        assert info.raw_data == {"extra": "data"}

    def test_user_info_optional_fields(self):
        """Test OAuthUserInfo with optional fields."""
        info = OAuthUserInfo(
            provider_user_id="user-456",
            email=None,
            name=None,
            avatar_url=None,
            raw_data={},
        )

        assert info.provider_user_id == "user-456"
        assert info.email is None
        assert info.name is None
        assert info.avatar_url is None
