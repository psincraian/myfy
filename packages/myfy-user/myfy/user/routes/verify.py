"""
Email verification routes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from myfy.user.errors import TokenExpiredError, TokenInvalidError

if TYPE_CHECKING:
    from myfy.user.config import UserSettings
    from myfy.user.services.user import UserService
    from myfy.web import Router


def register_routes(router: Router, settings: UserSettings) -> None:
    """Register email verification routes."""

    @router.get("/verify-email/{token}", name="user:verify_email")
    async def verify_email(
        request: Request,
        token: str,
        user_service: UserService,
        user_settings: UserSettings,
    ) -> JSONResponse | RedirectResponse:
        """
        Verify email address using token.

        This is called when user clicks the verification link in their email.
        """
        try:
            await user_service.verify_email_token(token)
        except TokenInvalidError:
            return JSONResponse(
                {"error": "Invalid verification link. Please request a new one."},
                status_code=400,
            )
        except TokenExpiredError:
            return JSONResponse(
                {"error": "This verification link has expired. Please request a new one."},
                status_code=400,
            )

        # Redirect to login or return success
        return JSONResponse({
            "message": "Your email has been verified. You can now log in.",
            "verified": True,
        })

    @router.post("/resend-verification", name="user:resend_verification")
    async def resend_verification(
        request: Request,
        user_service: UserService,
        user_settings: UserSettings,
    ) -> JSONResponse:
        """
        Resend verification email.

        Requires user to be logged in (session) or provide email.
        """
        # Get email from request body
        try:
            body = await request.json()
            email = body.get("email")
        except Exception:
            email = None

        if not email:
            return JSONResponse(
                {"error": "Email address is required"},
                status_code=400,
            )

        # Find user
        user = await user_service.get_by_email(email)
        if not user:
            # Don't reveal if user exists
            return JSONResponse({
                "message": "If an account exists with that email, "
                "a verification link has been sent.",
            })

        if user.email_verified:
            return JSONResponse({
                "message": "Email is already verified.",
            })

        # Create new verification token
        await user_service.create_verification_token(user.id)

        # TODO: Send email via EmailService/TasksModule

        return JSONResponse({
            "message": "If an account exists with that email, "
            "a verification link has been sent.",
        })
