"""
Session management for cookie-based authentication.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from starlette.requests import Request
from starlette.responses import Response

from myfy.user.errors import SessionExpiredError, SessionInvalidError

if TYPE_CHECKING:
    from myfy.user.config import UserSettings


class SessionManager:
    """
    Session manager for cookie-based authentication.

    Uses signed cookies with itsdangerous for secure session storage.

    Usage:
        ```python
        manager = SessionManager(settings)

        # Create session
        response = RedirectResponse("/")
        await manager.create_session(response, {"user_id": "123"})

        # Get session
        session = await manager.get_session(request)
        if session:
            user_id = session.get("user_id")

        # Destroy session
        await manager.destroy_session(request, response)
        ```
    """

    def __init__(
        self,
        secret_key: str,
        cookie_name: str = "myfy_session",
        lifetime: int = 604800,  # 7 days
        secure: bool = True,
        httponly: bool = True,
        samesite: str = "lax",
    ) -> None:
        """
        Initialize session manager.

        Args:
            secret_key: Secret key for signing session cookies
            cookie_name: Name of the session cookie
            lifetime: Session lifetime in seconds
            secure: Whether cookie requires HTTPS
            httponly: Whether cookie is HTTP-only
            samesite: SameSite attribute (strict, lax, none)
        """
        self._secret_key = secret_key
        self._cookie_name = cookie_name
        self._lifetime = lifetime
        self._secure = secure
        self._httponly = httponly
        self._samesite = samesite

        # Create serializer for signing cookies
        self._serializer = URLSafeTimedSerializer(secret_key)

    @classmethod
    def from_settings(cls, settings: UserSettings) -> SessionManager:
        """Create session manager from UserSettings."""
        return cls(
            secret_key=settings.secret_key.get_secret_value(),
            cookie_name=settings.session_cookie_name,
            lifetime=settings.session_lifetime,
            secure=settings.session_secure,
            httponly=settings.session_httponly,
            samesite=settings.session_samesite,
        )

    async def create_session(
        self,
        response: Response,
        data: dict[str, Any],
        remember: bool = False,
    ) -> None:
        """
        Create a new session and set cookie.

        Args:
            response: Response to set cookie on
            data: Session data to store
            remember: If True, use extended lifetime
        """
        # Add created timestamp
        session_data = {
            **data,
            "_created": datetime.now(UTC).isoformat(),
        }

        # Serialize and sign
        signed_value = self._serializer.dumps(session_data)

        # Calculate max age
        max_age = self._lifetime * 4 if remember else self._lifetime

        # Set cookie
        response.set_cookie(
            key=self._cookie_name,
            value=signed_value,
            max_age=max_age,
            secure=self._secure,
            httponly=self._httponly,
            samesite=self._samesite,
            path="/",
        )

    async def get_session(self, request: Request) -> dict[str, Any] | None:
        """
        Get session data from request.

        Args:
            request: Request to get session from

        Returns:
            Session data dict or None if no valid session

        Raises:
            SessionExpiredError: If session is expired
            SessionInvalidError: If session signature is invalid
        """
        cookie_value = request.cookies.get(self._cookie_name)
        if not cookie_value:
            return None

        try:
            # Deserialize and verify signature
            return self._serializer.loads(
                cookie_value,
                max_age=self._lifetime * 4,  # Allow extended sessions
            )
        except SignatureExpired as e:
            raise SessionExpiredError from e
        except BadSignature as e:
            raise SessionInvalidError from e

    async def get_session_safe(self, request: Request) -> dict[str, Any] | None:
        """
        Get session data without raising exceptions.

        Args:
            request: Request to get session from

        Returns:
            Session data dict or None if no valid session or error
        """
        try:
            return await self.get_session(request)
        except (SessionExpiredError, SessionInvalidError):
            return None

    async def destroy_session(
        self,
        request: Request,  # noqa: ARG002 - Kept for API consistency
        response: Response,
    ) -> None:
        """
        Destroy session by deleting cookie.

        Args:
            request: Request (unused, for API consistency)
            response: Response to delete cookie from
        """
        response.delete_cookie(
            key=self._cookie_name,
            path="/",
            secure=self._secure,
            httponly=self._httponly,
            samesite=self._samesite,
        )

    async def refresh_session(
        self,
        request: Request,
        response: Response,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """
        Refresh session with new expiration.

        Args:
            request: Request to get current session from
            response: Response to set new cookie on
            additional_data: Additional data to merge into session
        """
        session = await self.get_session_safe(request)
        if session:
            if additional_data:
                session.update(additional_data)
            await self.create_session(response, session)
