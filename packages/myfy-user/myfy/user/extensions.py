"""Extension protocols for myfy-user module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .oauth.registry import OAuthProviderRegistry
    from .services.user import UserService


@runtime_checkable
class IUserProvider(Protocol):
    """
    Protocol for modules that provide user management.

    Allows other modules to discover and use user services.
    """

    def get_user_service(self) -> UserService:
        """Get the user service for CRUD operations."""
        ...

    def get_oauth_registry(self) -> OAuthProviderRegistry:
        """Get OAuth provider registry."""
        ...
