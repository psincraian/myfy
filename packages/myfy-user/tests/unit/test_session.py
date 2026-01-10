"""Unit tests for SessionManager."""

from unittest.mock import MagicMock

import pytest

from myfy.user.auth.session import SessionManager
from myfy.user.errors import SessionInvalidError


class TestSessionManager:
    """Tests for SessionManager class."""

    @pytest.mark.asyncio
    async def test_create_session(self, session_manager, mock_response):
        """Test creating a session."""
        session_data = {"user_id": "user-123", "role": "admin"}

        await session_manager.create_session(mock_response, session_data)

        # Cookie should be set
        mock_response.set_cookie.assert_called_once()
        call_kwargs = mock_response.set_cookie.call_args.kwargs
        assert call_kwargs["key"] == "myfy_session"
        assert call_kwargs["httponly"] is True
        assert "value" in call_kwargs

    @pytest.mark.asyncio
    async def test_create_and_get_session(self, session_manager):
        """Test creating and retrieving session data."""
        session_data = {"user_id": "user-456", "email": "test@example.com"}

        # Create session and capture cookie value
        mock_response = MagicMock()
        await session_manager.create_session(mock_response, session_data)

        cookie_value = mock_response.set_cookie.call_args.kwargs["value"]

        # Create mock request with the cookie
        mock_request = MagicMock()
        mock_request.cookies = {"myfy_session": cookie_value}

        # Get session should return the data
        retrieved = await session_manager.get_session(mock_request)

        assert retrieved["user_id"] == "user-456"
        assert retrieved["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_session_no_cookie(self, session_manager, mock_request):
        """Test getting session when no cookie present."""
        mock_request.cookies = {}

        result = await session_manager.get_session(mock_request)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_invalid_cookie(self, session_manager, mock_request):
        """Test getting session with invalid cookie."""
        mock_request.cookies = {"myfy_session": "invalid-cookie-value"}

        with pytest.raises(SessionInvalidError):
            await session_manager.get_session(mock_request)

    @pytest.mark.asyncio
    async def test_get_session_tampered_cookie(self, session_manager, mock_request):
        """Test getting session with tampered cookie."""
        # Create valid session
        mock_response = MagicMock()
        await session_manager.create_session(mock_response, {"user_id": "123"})
        cookie_value = mock_response.set_cookie.call_args.kwargs["value"]

        # Tamper with the cookie
        tampered = cookie_value[:-10] + "tampered!"
        mock_request.cookies = {"myfy_session": tampered}

        with pytest.raises(SessionInvalidError):
            await session_manager.get_session(mock_request)

    @pytest.mark.asyncio
    async def test_get_session_safe_returns_none_on_error(self, session_manager, mock_request):
        """Test get_session_safe returns None instead of raising."""
        mock_request.cookies = {"myfy_session": "invalid"}

        result = await session_manager.get_session_safe(mock_request)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_safe_returns_data(self, session_manager):
        """Test get_session_safe returns data on success."""
        session_data = {"user_id": "user-789"}

        mock_response = MagicMock()
        await session_manager.create_session(mock_response, session_data)
        cookie_value = mock_response.set_cookie.call_args.kwargs["value"]

        mock_request = MagicMock()
        mock_request.cookies = {"myfy_session": cookie_value}

        result = await session_manager.get_session_safe(mock_request)
        assert result is not None
        assert result["user_id"] == "user-789"

    @pytest.mark.asyncio
    async def test_destroy_session(self, session_manager, mock_request, mock_response):
        """Test destroying a session."""
        await session_manager.destroy_session(mock_request, mock_response)

        mock_response.delete_cookie.assert_called_once()
        call_kwargs = mock_response.delete_cookie.call_args.kwargs
        assert call_kwargs["key"] == "myfy_session"

    @pytest.mark.asyncio
    async def test_session_with_complex_data(self, session_manager):
        """Test session with complex nested data."""
        session_data = {
            "user_id": "user-complex",
            "permissions": ["read", "write", "admin"],
            "metadata": {
                "login_time": "2024-01-01T00:00:00",
                "ip": "127.0.0.1",
            },
        }

        mock_response = MagicMock()
        await session_manager.create_session(mock_response, session_data)
        cookie_value = mock_response.set_cookie.call_args.kwargs["value"]

        mock_request = MagicMock()
        mock_request.cookies = {"myfy_session": cookie_value}

        retrieved = await session_manager.get_session(mock_request)

        assert retrieved["user_id"] == "user-complex"
        assert retrieved["permissions"] == ["read", "write", "admin"]
        assert retrieved["metadata"]["ip"] == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_custom_cookie_name(self, user_settings):
        """Test session manager with custom cookie name."""
        manager = SessionManager(
            secret_key=user_settings.secret_key.get_secret_value(),
            cookie_name="custom_session",
            lifetime=3600,
        )

        mock_response = MagicMock()
        await manager.create_session(mock_response, {"user_id": "123"})

        call_kwargs = mock_response.set_cookie.call_args.kwargs
        assert call_kwargs["key"] == "custom_session"

    @pytest.mark.asyncio
    async def test_session_secure_flag(self, user_settings):
        """Test session manager with secure flag."""
        manager = SessionManager(
            secret_key=user_settings.secret_key.get_secret_value(),
            cookie_name="session",
            lifetime=3600,
            secure=True,
        )

        mock_response = MagicMock()
        await manager.create_session(mock_response, {"user_id": "123"})

        call_kwargs = mock_response.set_cookie.call_args.kwargs
        assert call_kwargs["secure"] is True

    @pytest.mark.asyncio
    async def test_session_samesite_options(self, user_settings):
        """Test session manager with different samesite options."""
        for samesite in ["lax", "strict", "none"]:
            manager = SessionManager(
                secret_key=user_settings.secret_key.get_secret_value(),
                cookie_name="session",
                lifetime=3600,
                samesite=samesite,
            )

            mock_response = MagicMock()
            await manager.create_session(mock_response, {"user_id": "123"})

            call_kwargs = mock_response.set_cookie.call_args.kwargs
            assert call_kwargs["samesite"] == samesite


class TestSessionManagerRefresh:
    """Tests for session refresh functionality."""

    @pytest.mark.asyncio
    async def test_refresh_session(self, session_manager):
        """Test refreshing a session extends its lifetime."""
        session_data = {"user_id": "refresh-user"}

        # Create initial session
        mock_response1 = MagicMock()
        await session_manager.create_session(mock_response1, session_data)
        cookie_value = mock_response1.set_cookie.call_args.kwargs["value"]

        # Create request with session
        mock_request = MagicMock()
        mock_request.cookies = {"myfy_session": cookie_value}

        # Refresh session
        mock_response2 = MagicMock()

        await session_manager.refresh_session(mock_request, mock_response2)

        # New cookie should be set
        mock_response2.set_cookie.assert_called_once()
        new_cookie = mock_response2.set_cookie.call_args.kwargs["value"]

        # The cookie value changes (new timestamp)
        # but data should be preserved
        mock_request2 = MagicMock()
        mock_request2.cookies = {"myfy_session": new_cookie}

        retrieved = await session_manager.get_session(mock_request2)
        assert retrieved["user_id"] == "refresh-user"

    @pytest.mark.asyncio
    async def test_refresh_session_with_additional_data(self, session_manager):
        """Test refreshing session with additional data."""
        initial_data = {"user_id": "user-123"}

        mock_response1 = MagicMock()
        await session_manager.create_session(mock_response1, initial_data)
        cookie_value = mock_response1.set_cookie.call_args.kwargs["value"]

        mock_request = MagicMock()
        mock_request.cookies = {"myfy_session": cookie_value}

        mock_response2 = MagicMock()

        await session_manager.refresh_session(
            mock_request,
            mock_response2,
            additional_data={"last_activity": "2024-01-01"},
        )

        new_cookie = mock_response2.set_cookie.call_args.kwargs["value"]
        mock_request2 = MagicMock()
        mock_request2.cookies = {"myfy_session": new_cookie}

        retrieved = await session_manager.get_session(mock_request2)
        assert retrieved["user_id"] == "user-123"
        assert retrieved["last_activity"] == "2024-01-01"


class TestSessionManagerFromSettings:
    """Tests for creating session manager from settings."""

    def test_from_settings(self, user_settings):
        """Test creating SessionManager from UserSettings."""
        manager = SessionManager.from_settings(user_settings)

        assert manager._cookie_name == user_settings.session_cookie_name
        assert manager._lifetime == user_settings.session_lifetime
        assert manager._secure == user_settings.session_secure

    @pytest.mark.asyncio
    async def test_from_settings_creates_valid_session(self, user_settings):
        """Test that manager from settings creates valid sessions."""
        manager = SessionManager.from_settings(user_settings)

        mock_response = MagicMock()
        await manager.create_session(mock_response, {"user_id": "test"})

        cookie_value = mock_response.set_cookie.call_args.kwargs["value"]
        mock_request = MagicMock()
        mock_request.cookies = {user_settings.session_cookie_name: cookie_value}

        result = await manager.get_session(mock_request)
        assert result["user_id"] == "test"
