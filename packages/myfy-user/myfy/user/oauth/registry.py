"""
OAuth provider registry for managing configured providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from myfy.user.errors import OAuthProviderNotConfiguredError, OAuthProviderNotFoundError

from .base import OAuthProvider
from .github import GitHubOAuthProvider
from .google import GoogleOAuthProvider

if TYPE_CHECKING:
    from myfy.user.config import UserSettings


class OAuthProviderRegistry:
    """
    Registry of OAuth providers.

    Manages configured OAuth providers and provides lookup by name.

    Usage:
        ```python
        registry = OAuthProviderRegistry(settings)

        # Register enabled providers
        registry.register_provider("google")
        registry.register_provider("github")

        # Get provider by name
        provider = registry.get_provider("google")

        # List registered providers
        providers = registry.list_providers()
        ```
    """

    # Built-in provider classes
    _provider_classes: ClassVar[dict[str, type[OAuthProvider]]] = {
        "google": GoogleOAuthProvider,
        "github": GitHubOAuthProvider,
    }

    def __init__(self, settings: UserSettings) -> None:
        """
        Initialize registry.

        Args:
            settings: User settings containing OAuth configuration
        """
        self._settings = settings
        self._providers: dict[str, OAuthProvider] = {}

    def register_provider(self, name: str) -> None:
        """
        Register and configure an OAuth provider.

        Args:
            name: Provider name (e.g., 'google', 'github')

        Raises:
            OAuthProviderNotFoundError: If provider is unknown
            OAuthProviderNotConfiguredError: If provider settings are missing
        """
        if name not in self._provider_classes:
            available = ", ".join(self._provider_classes.keys())
            raise OAuthProviderNotFoundError(
                f"{name}. Available providers: {available}"
            )

        if not self._settings.is_oauth_provider_configured(name):
            raise OAuthProviderNotConfiguredError(name)

        # Get provider settings
        if name == "google":
            client_id = self._settings.oauth_google_client_id
            client_secret = self._settings.oauth_google_client_secret.get_secret_value()
            scopes = self._settings.oauth_google_scopes
        elif name == "github":
            client_id = self._settings.oauth_github_client_id
            client_secret = self._settings.oauth_github_client_secret.get_secret_value()
            scopes = self._settings.oauth_github_scopes
        else:
            raise OAuthProviderNotConfiguredError(name)

        # Create and register provider instance
        provider_class = self._provider_classes[name]
        self._providers[name] = provider_class(
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
        )

    def get_provider(self, name: str) -> OAuthProvider:
        """
        Get a registered provider.

        Args:
            name: Provider name

        Returns:
            OAuthProvider instance

        Raises:
            OAuthProviderNotFoundError: If provider is not registered
        """
        if name not in self._providers:
            raise OAuthProviderNotFoundError(name)
        return self._providers[name]

    def has_provider(self, name: str) -> bool:
        """
        Check if a provider is registered.

        Args:
            name: Provider name

        Returns:
            True if provider is registered
        """
        return name in self._providers

    def list_providers(self) -> list[str]:
        """
        List registered provider names.

        Returns:
            List of provider names
        """
        return list(self._providers.keys())

    def list_available_providers(self) -> list[str]:
        """
        List all available provider names (whether registered or not).

        Returns:
            List of available provider names
        """
        return list(self._provider_classes.keys())

    @classmethod
    def register_provider_class(
        cls,
        name: str,
        provider_class: type[OAuthProvider],
    ) -> None:
        """
        Register a custom provider class.

        Use this to add support for additional OAuth providers.

        Args:
            name: Provider name
            provider_class: Provider class

        Example:
            ```python
            class MyCustomProvider(BaseOAuthProvider):
                ...

            OAuthProviderRegistry.register_provider_class(
                "custom",
                MyCustomProvider,
            )
            ```
        """
        cls._provider_classes[name] = provider_class
