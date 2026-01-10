"""
User profile routes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse

from myfy.user.auth.provider import UserAuthenticated
from myfy.user.errors import PasswordTooWeakError

if TYPE_CHECKING:
    from myfy.user.config import UserSettings
    from myfy.user.services.user import UserService
    from myfy.web import Router


@dataclass
class UpdateProfileRequest:
    """Update profile form data."""

    display_name: str | None = None
    email: str | None = None


@dataclass
class ChangePasswordRequest:
    """Change password form data."""

    current_password: str
    new_password: str
    new_password_confirm: str


def register_routes(router: Router, settings: UserSettings) -> None:
    """Register profile routes."""

    @router.get("/profile", name="user:profile")
    async def get_profile(
        request: Request,
        user: UserAuthenticated,
        user_service: UserService,
    ) -> dict:
        """
        Get current user's profile.

        Requires authentication (returns 401 if not authenticated).
        """
        full_user = await user_service.get_by_id(user.id)
        if not full_user:
            return JSONResponse(
                {"error": "User not found"},
                status_code=404,
            )

        return {
            "id": full_user.id,
            "email": full_user.email,
            "email_verified": full_user.email_verified,
            "display_name": full_user.display_name,
            "is_superuser": full_user.is_superuser,
            "created_at": full_user.created_at.isoformat() if full_user.created_at else None,
            "last_login": full_user.last_login.isoformat() if full_user.last_login else None,
            "has_password": full_user.has_password(),
            "oauth_providers": [c.provider for c in full_user.oauth_connections],
        }

    @router.post("/profile", name="user:update_profile")
    async def update_profile(
        request: Request,
        data: UpdateProfileRequest,
        user: UserAuthenticated,
        user_service: UserService,
    ) -> JSONResponse:
        """
        Update current user's profile.

        Requires authentication.
        """
        updates = {}

        if data.display_name is not None:
            updates["display_name"] = data.display_name

        # Email changes should trigger re-verification
        # For now, we don't allow email changes through this endpoint
        if data.email is not None and data.email != user.email:
            return JSONResponse(
                {"error": "Email changes are not supported through this endpoint"},
                status_code=400,
            )

        if updates:
            await user_service.update(user.id, **updates)

        return JSONResponse({
            "message": "Profile updated successfully",
        })

    @router.post("/profile/change-password", name="user:change_password")
    async def change_password(
        request: Request,
        data: ChangePasswordRequest,
        user: UserAuthenticated,
        user_service: UserService,
    ) -> JSONResponse:
        """
        Change current user's password.

        Requires authentication and current password.
        """
        # Validate new passwords match
        if data.new_password != data.new_password_confirm:
            return JSONResponse(
                {"error": "New passwords do not match"},
                status_code=400,
            )

        # Verify current password
        full_user = await user_service.get_by_id(user.id)
        if not full_user:
            return JSONResponse(
                {"error": "User not found"},
                status_code=404,
            )

        if not full_user.has_password():
            return JSONResponse(
                {"error": "Account does not have a password set. "
                 "Use 'Set Password' instead."},
                status_code=400,
            )

        # Authenticate with current password
        from myfy.user.errors import InvalidCredentialsError

        try:
            await user_service.authenticate(user.email, data.current_password)
        except InvalidCredentialsError:
            return JSONResponse(
                {"error": "Current password is incorrect"},
                status_code=400,
            )

        # Set new password
        try:
            await user_service.set_password(user.id, data.new_password)
        except PasswordTooWeakError as e:
            return JSONResponse(
                {"error": str(e)},
                status_code=400,
            )

        return JSONResponse({
            "message": "Password changed successfully",
        })

    @router.post("/profile/set-password", name="user:set_password")
    async def set_password(
        request: Request,
        user: UserAuthenticated,
        user_service: UserService,
    ) -> JSONResponse:
        """
        Set password for OAuth-only users.

        Allows users who signed up via OAuth to add a password.
        """
        try:
            body = await request.json()
            new_password = body.get("password")
            new_password_confirm = body.get("password_confirm")
        except Exception:
            return JSONResponse(
                {"error": "Invalid request body"},
                status_code=400,
            )

        if not new_password or not new_password_confirm:
            return JSONResponse(
                {"error": "Password and confirmation are required"},
                status_code=400,
            )

        if new_password != new_password_confirm:
            return JSONResponse(
                {"error": "Passwords do not match"},
                status_code=400,
            )

        # Check if user already has a password
        full_user = await user_service.get_by_id(user.id)
        if full_user and full_user.has_password():
            return JSONResponse(
                {"error": "Account already has a password. Use 'Change Password' instead."},
                status_code=400,
            )

        # Set password
        try:
            await user_service.set_password(user.id, new_password)
        except PasswordTooWeakError as e:
            return JSONResponse(
                {"error": str(e)},
                status_code=400,
            )

        return JSONResponse({
            "message": "Password set successfully",
        })
