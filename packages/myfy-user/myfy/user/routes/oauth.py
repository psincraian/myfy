"""
OAuth routes: authorization and callback handling.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from myfy.user.errors import (
    OAuthError,
    OAuthProviderNotFoundError,
)

if TYPE_CHECKING:
    from myfy.user.auth.session import SessionManager
    from myfy.user.config import UserSettings
    from myfy.user.oauth.registry import OAuthProviderRegistry
    from myfy.user.services.user import UserService
    from myfy.web import Router


def register_routes(
    router: Router,
    settings: UserSettings,
    oauth_providers: list[str],
) -> None:
    """Register OAuth routes."""

    @router.get("/oauth/{provider}", name="user:oauth_authorize")
    async def oauth_authorize(
        request: Request,
        provider: str,
        oauth_registry: OAuthProviderRegistry,
        session_manager: SessionManager,
        user_settings: UserSettings,
    ) -> RedirectResponse | JSONResponse:
        """
        Redirect to OAuth provider for authorization.

        This initiates the OAuth flow by redirecting to the provider's
        authorization page.
        """
        try:
            oauth_provider = oauth_registry.get_provider(provider)
        except OAuthProviderNotFoundError:
            return JSONResponse(
                {"error": f"OAuth provider '{provider}' is not available"},
                status_code=404,
            )

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Build callback URL
        callback_url = str(request.url_for("user:oauth_callback", provider=provider))

        # Store state in session for verification
        response = RedirectResponse(
            oauth_provider.get_authorization_url(state, callback_url),
            status_code=302,
        )

        # Set state in a temporary cookie
        response.set_cookie(
            key=f"oauth_state_{provider}",
            value=state,
            max_age=600,  # 10 minutes
            secure=user_settings.session_secure,
            httponly=True,
            samesite="lax",
        )

        return response

    @router.get("/oauth/{provider}/callback", name="user:oauth_callback")
    async def oauth_callback(  # noqa: PLR0911 - OAuth callback requires multiple error conditions
        request: Request,
        provider: str,
        oauth_registry: OAuthProviderRegistry,
        user_service: UserService,
        session_manager: SessionManager,
        user_settings: UserSettings,
    ) -> RedirectResponse | JSONResponse:
        """
        Handle OAuth callback from provider.

        This completes the OAuth flow:
        1. Verifies state for CSRF protection
        2. Exchanges code for tokens
        3. Gets user info from provider
        4. Creates or links user account
        5. Creates session and redirects
        """
        # Get OAuth provider
        try:
            oauth_provider = oauth_registry.get_provider(provider)
        except OAuthProviderNotFoundError:
            return JSONResponse(
                {"error": f"OAuth provider '{provider}' is not available"},
                status_code=404,
            )

        # Get parameters from callback
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")

        # Handle OAuth errors
        if error:
            error_description = request.query_params.get("error_description", error)
            return JSONResponse(
                {"error": f"OAuth authorization failed: {error_description}"},
                status_code=400,
            )

        # Verify state
        expected_state = request.cookies.get(f"oauth_state_{provider}")
        if not state or state != expected_state:
            return JSONResponse(
                {"error": "Invalid OAuth state - possible CSRF attack"},
                status_code=400,
            )

        if not code:
            return JSONResponse(
                {"error": "Missing authorization code"},
                status_code=400,
            )

        # Exchange code for tokens
        callback_url = str(request.url_for("user:oauth_callback", provider=provider))

        try:
            tokens = await oauth_provider.exchange_code(code, callback_url)
            access_token = tokens.get("access_token")
            if not access_token:
                return JSONResponse(
                    {"error": "OAuth provider did not return access token"},
                    status_code=400,
                )

            # Get user info from provider
            user_info = await oauth_provider.get_user_info(access_token)

        except OAuthError as e:
            return JSONResponse(
                {"error": str(e)},
                status_code=400,
            )

        # Find or create user


        # Check if OAuth connection exists
        oauth_connection = await _find_oauth_connection(
            user_service,
            provider,
            user_info.provider_user_id,
        )

        if oauth_connection:
            # Update tokens
            oauth_connection.access_token = access_token
            oauth_connection.refresh_token = tokens.get("refresh_token")
            if "expires_in" in tokens:
                from datetime import timedelta

                oauth_connection.token_expires_at = datetime.now(UTC) + timedelta(
                    seconds=int(tokens["expires_in"])
                )
            oauth_connection.email = user_info.email
            oauth_connection.name = user_info.name
            oauth_connection.avatar_url = user_info.avatar_url

            user = await user_service.get_by_id(oauth_connection.user_id)

        else:
            # Check if user with email exists
            if user_info.email:
                user = await user_service.get_by_email(user_info.email)
            else:
                user = None

            if user:
                # Link OAuth to existing user
                oauth_connection = await _create_oauth_connection(
                    user_service,
                    user.id,
                    provider,
                    user_info,
                    access_token,
                    tokens,
                )
            else:
                # Create new user
                if not user_settings.allow_registration:
                    return JSONResponse(
                        {"error": "Registration is disabled"},
                        status_code=403,
                    )

                user = await user_service.create(
                    email=user_info.email or f"{user_info.provider_user_id}@{provider}.oauth",
                    password=None,  # OAuth-only user
                    display_name=user_info.name,
                    email_verified=bool(user_info.email),  # Trust provider's email
                )

                # Create OAuth connection
                oauth_connection = await _create_oauth_connection(
                    user_service,
                    user.id,
                    provider,
                    user_info,
                    access_token,
                    tokens,
                )

        # Update last login
        await user_service.update_last_login(user.id)

        # Create session
        response = RedirectResponse(
            user_settings.after_login_url,
            status_code=303,
        )

        # Clear OAuth state cookie
        response.delete_cookie(f"oauth_state_{provider}")

        await session_manager.create_session(
            response,
            {"user_id": user.id},
        )

        return response


async def _find_oauth_connection(
    user_service: UserService,
    provider: str,
    provider_user_id: str,
):
    """Find existing OAuth connection."""
    from sqlalchemy import select

    from myfy.user.models.oauth import OAuthConnection

    result = await user_service._session.execute(
        select(OAuthConnection).where(
            OAuthConnection.provider == provider,
            OAuthConnection.provider_user_id == provider_user_id,
        )
    )
    return result.scalar_one_or_none()


async def _create_oauth_connection(
    user_service: UserService,
    user_id: str,
    provider: str,
    user_info,
    access_token: str,
    tokens: dict,
):
    """Create OAuth connection for user."""
    import uuid
    from datetime import timedelta

    from myfy.user.models.oauth import OAuthConnection

    expires_at = None
    if "expires_in" in tokens:
        expires_at = datetime.now(UTC) + timedelta(seconds=int(tokens["expires_in"]))

    connection = OAuthConnection(
        id=str(uuid.uuid4()),
        user_id=user_id,
        provider=provider,
        provider_user_id=user_info.provider_user_id,
        access_token=access_token,
        refresh_token=tokens.get("refresh_token"),
        token_expires_at=expires_at,
        email=user_info.email,
        name=user_info.name,
        avatar_url=user_info.avatar_url,
    )

    user_service._session.add(connection)
    await user_service._session.commit()
    return connection
