"""Unit tests for user models."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from myfy.user.models.base import BaseUser, DefaultUser
from myfy.user.models.token import EmailVerificationToken, PasswordResetToken


class TestBaseUserMethods:
    """Tests for BaseUser helper methods."""

    def test_has_password_with_hash(self):
        """Test has_password returns True when hash exists."""
        user = MagicMock(spec=BaseUser)
        user.password_hash = "$argon2id$..."
        # Call the actual method
        result = BaseUser.has_password(user)
        assert result is True

    def test_has_password_without_hash(self):
        """Test has_password returns False when no hash."""
        user = MagicMock(spec=BaseUser)
        user.password_hash = None
        result = BaseUser.has_password(user)
        assert result is False

    def test_has_oauth_with_connections(self):
        """Test has_oauth returns True when connections exist."""
        user = MagicMock(spec=BaseUser)
        oauth_conn = MagicMock()
        oauth_conn.provider = "google"
        user.oauth_connections = [oauth_conn]

        result = BaseUser.has_oauth(user, None)
        assert result is True

    def test_has_oauth_no_connections(self):
        """Test has_oauth returns False when no connections."""
        user = MagicMock(spec=BaseUser)
        user.oauth_connections = []

        result = BaseUser.has_oauth(user, None)
        assert result is False

    def test_has_oauth_specific_provider(self):
        """Test has_oauth with specific provider."""
        user = MagicMock(spec=BaseUser)
        google_conn = MagicMock()
        google_conn.provider = "google"
        user.oauth_connections = [google_conn]

        assert BaseUser.has_oauth(user, "google") is True
        assert BaseUser.has_oauth(user, "github") is False


class TestEmailVerificationToken:
    """Tests for EmailVerificationToken model."""

    def test_create_token(self):
        """Test creating a verification token."""
        token = EmailVerificationToken.create(user_id="user-123")

        assert token.user_id == "user-123"
        assert token.token is not None
        assert len(token.token) > 20
        assert token.expires_at > datetime.now(UTC)
        assert token.used_at is None

    def test_create_token_custom_expiry(self):
        """Test creating token with custom expiry."""
        token = EmailVerificationToken.create(
            user_id="user-123",
            expires_in_seconds=60,  # 1 minute
        )

        # Should expire in about 1 minute
        expected = datetime.now(UTC) + timedelta(seconds=60)
        assert abs((token.expires_at - expected).total_seconds()) < 2

    def test_is_expired_false(self):
        """Test is_expired returns False for fresh token."""
        token = EmailVerificationToken.create(user_id="user-123")
        assert token.is_expired is False

    def test_is_expired_true(self):
        """Test is_expired returns True for expired token."""
        token = EmailVerificationToken.create(
            user_id="user-123",
            expires_in_seconds=-1,  # Already expired
        )
        assert token.is_expired is True

    def test_is_used_false(self):
        """Test is_used returns False for unused token."""
        token = EmailVerificationToken.create(user_id="user-123")
        assert token.is_used is False

    def test_is_used_true(self):
        """Test is_used returns True after mark_used."""
        token = EmailVerificationToken.create(user_id="user-123")
        token.mark_used()
        assert token.is_used is True
        assert token.used_at is not None

    def test_is_valid_fresh_token(self):
        """Test is_valid returns True for fresh token."""
        token = EmailVerificationToken.create(user_id="user-123")
        assert token.is_valid is True

    def test_is_valid_expired_token(self):
        """Test is_valid returns False for expired token."""
        token = EmailVerificationToken.create(
            user_id="user-123",
            expires_in_seconds=-1,
        )
        assert token.is_valid is False

    def test_is_valid_used_token(self):
        """Test is_valid returns False for used token."""
        token = EmailVerificationToken.create(user_id="user-123")
        token.mark_used()
        assert token.is_valid is False

    def test_token_uniqueness(self):
        """Test that tokens are unique."""
        token1 = EmailVerificationToken.create(user_id="user-123")
        token2 = EmailVerificationToken.create(user_id="user-123")
        assert token1.token != token2.token

    def test_token_repr(self):
        """Test token string representation."""
        token = EmailVerificationToken.create(user_id="user-123")
        repr_str = repr(token)
        assert "EmailVerificationToken" in repr_str
        assert token.id in repr_str


class TestPasswordResetToken:
    """Tests for PasswordResetToken model."""

    def test_create_token(self):
        """Test creating a password reset token."""
        token = PasswordResetToken.create(user_id="user-456")

        assert token.user_id == "user-456"
        assert token.token is not None
        assert len(token.token) > 20
        assert token.expires_at > datetime.now(UTC)
        assert token.used_at is None
        # invalidated defaults via database, so it may be None until persisted
        assert not token.invalidated  # Falsy check

    def test_create_token_custom_expiry(self):
        """Test creating token with custom expiry."""
        token = PasswordResetToken.create(
            user_id="user-456",
            expires_in_seconds=300,  # 5 minutes
        )

        expected = datetime.now(UTC) + timedelta(seconds=300)
        assert abs((token.expires_at - expected).total_seconds()) < 2

    def test_default_expiry_one_hour(self):
        """Test default expiry is about 1 hour."""
        token = PasswordResetToken.create(user_id="user-456")

        expected = datetime.now(UTC) + timedelta(hours=1)
        assert abs((token.expires_at - expected).total_seconds()) < 2

    def test_is_expired_false(self):
        """Test is_expired returns False for fresh token."""
        token = PasswordResetToken.create(user_id="user-456")
        assert token.is_expired is False

    def test_is_expired_true(self):
        """Test is_expired returns True for expired token."""
        token = PasswordResetToken.create(
            user_id="user-456",
            expires_in_seconds=-1,
        )
        assert token.is_expired is True

    def test_is_used_false(self):
        """Test is_used returns False for unused token."""
        token = PasswordResetToken.create(user_id="user-456")
        assert token.is_used is False

    def test_is_used_true(self):
        """Test is_used returns True after mark_used."""
        token = PasswordResetToken.create(user_id="user-456")
        token.mark_used()
        assert token.is_used is True

    def test_is_valid_fresh_token(self):
        """Test is_valid returns True for fresh token."""
        token = PasswordResetToken.create(user_id="user-456")
        assert token.is_valid is True

    def test_is_valid_expired_token(self):
        """Test is_valid returns False for expired token."""
        token = PasswordResetToken.create(
            user_id="user-456",
            expires_in_seconds=-1,
        )
        assert token.is_valid is False

    def test_is_valid_used_token(self):
        """Test is_valid returns False for used token."""
        token = PasswordResetToken.create(user_id="user-456")
        token.mark_used()
        assert token.is_valid is False

    def test_is_valid_invalidated_token(self):
        """Test is_valid returns False for invalidated token."""
        token = PasswordResetToken.create(user_id="user-456")
        token.invalidate()
        assert token.is_valid is False
        assert token.invalidated is True

    def test_invalidate(self):
        """Test invalidating a token."""
        token = PasswordResetToken.create(user_id="user-456")
        assert not token.invalidated  # Falsy initially

        token.invalidate()

        assert token.invalidated is True

    def test_token_uniqueness(self):
        """Test that tokens are unique."""
        token1 = PasswordResetToken.create(user_id="user-456")
        token2 = PasswordResetToken.create(user_id="user-456")
        assert token1.token != token2.token

    def test_token_repr(self):
        """Test token string representation."""
        token = PasswordResetToken.create(user_id="user-456")
        repr_str = repr(token)
        assert "PasswordResetToken" in repr_str
        assert token.id in repr_str


class TestDefaultUser:
    """Tests for DefaultUser model."""

    def test_default_user_tablename(self):
        """Test DefaultUser uses 'users' table."""
        assert DefaultUser.__tablename__ == "users"

    def test_default_user_inherits_base_user(self):
        """Test DefaultUser inherits from BaseUser."""
        assert issubclass(DefaultUser, BaseUser)

    def test_base_user_is_abstract(self):
        """Test BaseUser is abstract."""
        assert BaseUser.__abstract__ is True
