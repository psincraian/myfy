"""
Authentication routes: login, logout, register.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from myfy.user.auth.session import SessionManager
from myfy.user.config import UserSettings
from myfy.user.errors import (
    InvalidCredentialsError,
    PasswordTooWeakError,
    UserAlreadyExistsError,
)
from myfy.user.services.user import UserService

if TYPE_CHECKING:
    from myfy.web import Router


@dataclass
class LoginRequest:
    """Login form data."""

    email: str
    password: str
    remember: bool = False


@dataclass
class RegisterRequest:
    """Registration form data."""

    email: str
    password: str
    password_confirm: str
    display_name: str | None = None


def register_routes(router: Router, settings: UserSettings) -> None:
    """Register authentication routes."""

    @router.get("/login", name="user:login")
    async def login_page(
        request: Request,
        user_settings: UserSettings,
    ) -> dict:
        """
        Login page data.

        Returns JSON for API or can be used with templates.
        """
        return {
            "allow_registration": user_settings.allow_registration,
            "allow_password_login": user_settings.allow_password_login,
            "oauth_providers": user_settings.get_configured_oauth_providers(),
            "register_url": user_settings.register_url,
        }

    @router.post("/login", name="user:login_submit")
    async def login(
        request: Request,
        data: LoginRequest,
        user_service: UserService,
        session_manager: SessionManager,
        user_settings: UserSettings,
    ) -> RedirectResponse | JSONResponse:
        """Handle login form submission."""
        if not user_settings.allow_password_login:
            return JSONResponse(
                {"error": "Password login is disabled"},
                status_code=403,
            )

        try:
            user = await user_service.authenticate(data.email, data.password)
        except InvalidCredentialsError:
            return JSONResponse(
                {"error": "Invalid email or password"},
                status_code=401,
            )

        # Check email verification if required
        if user_settings.require_email_verification and not user.email_verified:
            return JSONResponse(
                {"error": "Please verify your email address before logging in"},
                status_code=403,
            )

        # Update last login
        await user_service.update_last_login(user.id)

        # Create session
        response = RedirectResponse(
            user_settings.after_login_url,
            status_code=303,
        )
        await session_manager.create_session(
            response,
            {"user_id": user.id},
            remember=data.remember,
        )

        return response

    @router.post("/logout", name="user:logout")
    async def logout(
        request: Request,
        session_manager: SessionManager,
        user_settings: UserSettings,
    ) -> RedirectResponse:
        """Handle logout."""
        response = RedirectResponse(
            user_settings.after_logout_url,
            status_code=303,
        )
        await session_manager.destroy_session(request, response)
        return response

    @router.get("/register", name="user:register")
    async def register_page(
        request: Request,
        user_settings: UserSettings,
    ) -> dict | RedirectResponse:
        """
        Registration page data.

        Returns JSON for API or can be used with templates.
        """
        if not user_settings.allow_registration:
            return RedirectResponse(user_settings.login_url, status_code=303)

        return {
            "allow_registration": user_settings.allow_registration,
            "oauth_providers": user_settings.get_configured_oauth_providers(),
            "login_url": user_settings.login_url,
        }

    @router.post("/register", name="user:register_submit")
    async def register(
        request: Request,
        data: RegisterRequest,
        user_service: UserService,
        user_settings: UserSettings,
    ) -> JSONResponse | RedirectResponse:
        """Handle registration form submission."""
        if not user_settings.allow_registration:
            return JSONResponse(
                {"error": "Registration is disabled"},
                status_code=403,
            )

        # Validate passwords match
        if data.password != data.password_confirm:
            return JSONResponse(
                {"error": "Passwords do not match"},
                status_code=400,
            )

        try:
            # Create user
            user = await user_service.create(
                email=data.email,
                password=data.password,
                display_name=data.display_name,
            )
        except UserAlreadyExistsError:
            return JSONResponse(
                {"error": "An account with this email already exists"},
                status_code=400,
            )
        except PasswordTooWeakError as e:
            return JSONResponse(
                {"error": str(e)},
                status_code=400,
            )

        # Send verification email if required
        if user_settings.require_email_verification:
            await user_service.create_verification_token(user.id)
            # TODO: Send email via EmailService/TasksModule
            return JSONResponse({
                "message": "Please check your email to verify your account",
                "user_id": user.id,
            })

        # If no verification required, redirect to login or after_register_url
        return RedirectResponse(
            user_settings.after_register_url,
            status_code=303,
        )
