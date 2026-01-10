"""
OAuth provider implementations for myfy-user.

Provides OAuth 2.0 integration with Google, GitHub, and extensible for others.
"""

from .base import BaseOAuthProvider, OAuthProvider, OAuthUserInfo
from .github import GitHubOAuthProvider
from .google import GoogleOAuthProvider
from .registry import OAuthProviderRegistry

__all__ = [
    "BaseOAuthProvider",
    "GitHubOAuthProvider",
    "GoogleOAuthProvider",
    "OAuthProvider",
    "OAuthProviderRegistry",
    "OAuthUserInfo",
]
