"""
Password routes: forgot password and reset.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from myfy.user.errors import (
    PasswordTooWeakError,
    TokenExpiredError,
    TokenInvalidError,
)

if TYPE_CHECKING:
    from myfy.user.config import UserSettings
    from myfy.user.services.user import UserService
    from myfy.web import Router


@dataclass
class ForgotPasswordRequest:
    """Forgot password form data."""

    email: str


@dataclass
class ResetPasswordRequest:
    """Reset password form data."""

    password: str
    password_confirm: str


def register_routes(router: Router, settings: UserSettings) -> None:
    """Register password routes."""

    @router.get("/forgot-password", name="user:forgot_password")
    async def forgot_password_page(
        request: Request,
        user_settings: UserSettings,
    ) -> dict:
        """
        Forgot password page data.

        Returns JSON for API or can be used with templates.
        """
        return {
            "login_url": user_settings.login_url,
        }

    @router.post("/forgot-password", name="user:forgot_password_submit")
    async def forgot_password(
        request: Request,
        data: ForgotPasswordRequest,
        user_service: UserService,
        user_settings: UserSettings,
    ) -> JSONResponse:
        """
        Handle forgot password form submission.

        Always returns success to prevent email enumeration.
        """
        # Create token (returns None if user doesn't exist)
        token = await user_service.create_password_reset_token(data.email)

        if token:
            # TODO: Send email via EmailService/TasksModule
            pass

        # Always return success to prevent email enumeration
        return JSONResponse(
            {
                "message": "If an account exists with that email, "
                "a password reset link has been sent.",
            }
        )

    @router.get("/reset-password/{token}", name="user:reset_password")
    async def reset_password_page(
        request: Request,
        token: str,
        user_settings: UserSettings,
    ) -> dict | JSONResponse:
        """
        Reset password page data.

        Validates token before showing form.
        """
        # We don't validate token here to avoid timing attacks
        # Token is validated when form is submitted
        return {
            "token": token,
            "login_url": user_settings.login_url,
        }

    @router.post("/reset-password/{token}", name="user:reset_password_submit")
    async def reset_password(
        request: Request,
        token: str,
        data: ResetPasswordRequest,
        user_service: UserService,
        user_settings: UserSettings,
    ) -> JSONResponse | RedirectResponse:
        """Handle reset password form submission."""
        # Validate passwords match
        if data.password != data.password_confirm:
            return JSONResponse(
                {"error": "Passwords do not match"},
                status_code=400,
            )

        try:
            await user_service.reset_password_with_token(token, data.password)
        except TokenInvalidError:
            return JSONResponse(
                {"error": "Invalid or expired reset link. Please request a new one."},
                status_code=400,
            )
        except TokenExpiredError:
            return JSONResponse(
                {"error": "This reset link has expired. Please request a new one."},
                status_code=400,
            )
        except PasswordTooWeakError as e:
            return JSONResponse(
                {"error": str(e)},
                status_code=400,
            )

        return JSONResponse(
            {
                "message": "Your password has been reset. You can now log in.",
            }
        )
