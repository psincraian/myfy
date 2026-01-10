"""
Authenticated provider for AuthModule integration.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from starlette.requests import Request

from myfy.web.auth.types import Authenticated

if TYPE_CHECKING:
    from myfy.user.config import UserSettings
    from myfy.user.models.base import BaseUser

    from .jwt import JWTService
    from .session import SessionManager


@dataclass
class UserAuthenticated(Authenticated):
    """
    Authenticated user type for DI injection.

    Extends the base Authenticated type with user-specific fields.
    """

    id: str
    email: str
    is_superuser: bool
    display_name: str | None = None
    email_verified: bool = True


def create_authenticated_provider(
    user_model: type[BaseUser],  # noqa: ARG001 - Reserved for future type-based queries
) -> Callable[..., Authenticated | None]:
    """
    Create an authenticated_provider function for AuthModule.

    This factory returns a function that:
    1. Checks for session cookie (web UI)
    2. Checks for JWT bearer token (API)
    3. Loads user from database if valid
    4. Returns UserAuthenticated instance or None

    Usage with UserModule:
        ```python
        user_module = UserModule()

        app.add_module(AuthModule(
            authenticated_provider=user_module.get_authenticated_provider(),
        ))
        ```

    Args:
        user_model: The User model class to use

    Returns:
        Provider function for AuthModule
    """
    from myfy.user.services.user import UserService

    async def authenticated_provider(
        request: Request,
        session_manager: SessionManager,
        jwt_service: JWTService,
        user_service: UserService,
        settings: UserSettings,
    ) -> Authenticated | None:
        """
        Provide authenticated user for routes.

        Checks:
        1. Session cookie (for web UI)
        2. Authorization header with Bearer token (for API)

        Returns:
            UserAuthenticated if valid session/token, None otherwise
        """
        # Try session authentication first (web UI)
        session_data = await session_manager.get_session_safe(request)
        if session_data and "user_id" in session_data:
            user = await user_service.get_by_id(session_data["user_id"])
            if user and user.is_active:
                # Check email verification if required
                if settings.require_email_verification and not user.email_verified:
                    return None

                return UserAuthenticated(
                    id=user.id,
                    email=user.email,
                    is_superuser=user.is_superuser,
                    display_name=user.display_name,
                    email_verified=user.email_verified,
                )

        # Try JWT authentication (API)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = jwt_service.decode_token_safe(token)
            if payload and payload.get("type") == "access" and "sub" in payload:
                user = await user_service.get_by_id(payload["sub"])
                if user and user.is_active:
                    # Check email verification if required
                    if settings.require_email_verification and not user.email_verified:
                        return None

                    return UserAuthenticated(
                        id=user.id,
                        email=user.email,
                        is_superuser=user.is_superuser,
                        display_name=user.display_name,
                        email_verified=user.email_verified,
                    )

        return None

    return authenticated_provider
