"""Unit tests for JWTService."""

import time

import pytest

from myfy.user.auth.jwt import JWTService
from myfy.user.errors import TokenExpiredError, TokenInvalidError


class TestJWTService:
    """Tests for JWTService class."""

    def test_create_access_token(self, jwt_service):
        """Test creating an access token."""
        token = jwt_service.create_access_token(
            user_id="user-123",
            additional_claims={"role": "admin"},
        )

        assert isinstance(token, str)
        assert len(token) > 50
        # JWT has 3 parts separated by dots
        assert len(token.split(".")) == 3

    def test_create_refresh_token(self, jwt_service):
        """Test creating a refresh token."""
        token = jwt_service.create_refresh_token(user_id="user-456")

        assert isinstance(token, str)
        assert len(token) > 50

    def test_decode_access_token(self, jwt_service):
        """Test decoding a valid access token."""
        token = jwt_service.create_access_token(
            user_id="decode-user",
            additional_claims={"email": "test@example.com"},
        )

        payload = jwt_service.decode_access_token(token)

        assert payload["sub"] == "decode-user"
        assert payload["type"] == "access"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_refresh_token(self, jwt_service):
        """Test decoding a valid refresh token."""
        token = jwt_service.create_refresh_token(user_id="refresh-user")

        payload = jwt_service.decode_refresh_token(token)

        assert payload["sub"] == "refresh-user"
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self, jwt_service):
        """Test decoding an invalid token raises error."""
        with pytest.raises(TokenInvalidError):
            jwt_service.decode_access_token("not-a-valid-token")

    def test_decode_tampered_token(self, jwt_service):
        """Test decoding a tampered token raises error."""
        token = jwt_service.create_access_token(user_id="user-123")

        # Tamper with the token
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + ".tampered"

        with pytest.raises(TokenInvalidError):
            jwt_service.decode_access_token(tampered)

    def test_decode_token_wrong_secret(self, user_settings):
        """Test decoding token with wrong secret raises error."""
        # Create token with one secret
        service1 = JWTService(
            secret_key="secret-key-one-32-characters-long",
            algorithm="HS256",
        )
        token = service1.create_access_token(user_id="user-123")

        # Try to decode with different secret
        service2 = JWTService(
            secret_key="different-secret-key-32-chars!!!",
            algorithm="HS256",
        )

        with pytest.raises(TokenInvalidError):
            service2.decode_access_token(token)

    def test_decode_token_safe_returns_none_on_error(self, jwt_service):
        """Test decode_token_safe returns None instead of raising."""
        result = jwt_service.decode_token_safe("invalid-token")
        assert result is None

    def test_decode_token_safe_returns_payload(self, jwt_service):
        """Test decode_token_safe returns payload on success."""
        token = jwt_service.create_access_token(user_id="safe-user")

        payload = jwt_service.decode_token_safe(token)

        assert payload is not None
        assert payload["sub"] == "safe-user"

    def test_expired_token(self, user_settings):
        """Test that expired tokens raise TokenExpiredError."""
        # Create service with very short lifetime
        service = JWTService(
            secret_key=user_settings.secret_key.get_secret_value(),
            algorithm="HS256",
            access_token_lifetime=1,  # 1 second
        )

        token = service.create_access_token(user_id="expire-user")

        # Wait for token to expire
        time.sleep(2)

        with pytest.raises(TokenExpiredError):
            service.decode_access_token(token)

    def test_token_contains_expiration(self, jwt_service):
        """Test that tokens contain expiration claim."""
        token = jwt_service.create_access_token(user_id="user-123")
        payload = jwt_service.decode_access_token(token)

        assert "exp" in payload
        # Expiration should be in the future
        assert payload["exp"] > time.time()

    def test_token_contains_issued_at(self, jwt_service):
        """Test that tokens contain issued_at claim."""
        before = int(time.time())
        token = jwt_service.create_access_token(user_id="user-123")
        after = int(time.time())

        payload = jwt_service.decode_access_token(token)

        assert "iat" in payload
        # iat is a datetime in the payload, convert to timestamp for comparison
        iat_ts = (
            int(payload["iat"].timestamp())
            if hasattr(payload["iat"], "timestamp")
            else int(payload["iat"])
        )
        assert before <= iat_ts <= after + 1

    def test_access_vs_refresh_token_type(self, jwt_service):
        """Test that access and refresh tokens have correct types."""
        access_token = jwt_service.create_access_token(user_id="user-123")
        refresh_token = jwt_service.create_refresh_token(user_id="user-123")

        access_payload = jwt_service.decode_access_token(access_token)
        refresh_payload = jwt_service.decode_refresh_token(refresh_token)

        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"

    def test_refresh_token_longer_lifetime(self, user_settings):
        """Test that refresh tokens have longer lifetime than access tokens."""
        service = JWTService(
            secret_key=user_settings.secret_key.get_secret_value(),
            algorithm="HS256",
            access_token_lifetime=3600,  # 1 hour
            refresh_token_lifetime=86400,  # 24 hours
        )

        access_token = service.create_access_token(user_id="user-123")
        refresh_token = service.create_refresh_token(user_id="user-123")

        access_payload = service.decode_access_token(access_token)
        refresh_payload = service.decode_refresh_token(refresh_token)

        # Get exp as timestamp
        access_exp = (
            access_payload["exp"].timestamp()
            if hasattr(access_payload["exp"], "timestamp")
            else access_payload["exp"]
        )
        refresh_exp = (
            refresh_payload["exp"].timestamp()
            if hasattr(refresh_payload["exp"], "timestamp")
            else refresh_payload["exp"]
        )

        # Refresh token expiration should be later
        assert refresh_exp > access_exp

    def test_custom_claims_in_access_token(self, jwt_service):
        """Test adding custom claims to access token."""
        custom_claims = {
            "role": "admin",
            "permissions": ["read", "write"],
            "org_id": "org-456",
        }

        token = jwt_service.create_access_token(
            user_id="user-123",
            additional_claims=custom_claims,
        )

        payload = jwt_service.decode_access_token(token)

        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]
        assert payload["org_id"] == "org-456"


class TestJWTRefreshAccessToken:
    """Tests for refreshing access tokens."""

    def test_refresh_access_token(self, jwt_service):
        """Test refreshing an access token from a refresh token."""
        refresh_token = jwt_service.create_refresh_token(user_id="refresh-user")

        new_access = jwt_service.refresh_access_token(refresh_token)

        assert isinstance(new_access, str)
        payload = jwt_service.decode_access_token(new_access)
        assert payload["sub"] == "refresh-user"
        assert payload["type"] == "access"

    def test_refresh_access_token_invalid_refresh(self, jwt_service):
        """Test refreshing with invalid refresh token."""
        with pytest.raises(TokenInvalidError):
            jwt_service.refresh_access_token("invalid-token")

    def test_refresh_access_token_with_access_token(self, jwt_service):
        """Test that using access token for refresh fails."""
        access_token = jwt_service.create_access_token(user_id="user-123")

        with pytest.raises(TokenInvalidError):
            jwt_service.refresh_access_token(access_token)


class TestJWTAlgorithms:
    """Tests for different JWT algorithms."""

    def test_hs256_algorithm(self, user_settings):
        """Test JWT with HS256 algorithm."""
        service = JWTService(
            secret_key=user_settings.secret_key.get_secret_value(),
            algorithm="HS256",
        )

        token = service.create_access_token(user_id="hs256-user")
        payload = service.decode_access_token(token)

        assert payload["sub"] == "hs256-user"

    def test_hs384_algorithm(self, user_settings):
        """Test JWT with HS384 algorithm."""
        service = JWTService(
            secret_key=user_settings.secret_key.get_secret_value(),
            algorithm="HS384",
        )

        token = service.create_access_token(user_id="hs384-user")
        payload = service.decode_access_token(token)

        assert payload["sub"] == "hs384-user"

    def test_hs512_algorithm(self, user_settings):
        """Test JWT with HS512 algorithm."""
        service = JWTService(
            secret_key=user_settings.secret_key.get_secret_value(),
            algorithm="HS512",
        )

        token = service.create_access_token(user_id="hs512-user")
        payload = service.decode_access_token(token)

        assert payload["sub"] == "hs512-user"


class TestJWTFromSettings:
    """Tests for creating JWT service from settings."""

    def test_from_settings(self, user_settings):
        """Test creating JWTService from UserSettings."""
        service = JWTService.from_settings(user_settings)

        assert service._algorithm == user_settings.jwt_algorithm
        assert service._access_token_lifetime == user_settings.jwt_access_token_lifetime
        assert service._refresh_token_lifetime == user_settings.jwt_refresh_token_lifetime

    def test_from_settings_creates_valid_tokens(self, user_settings):
        """Test that service from settings creates valid tokens."""
        service = JWTService.from_settings(user_settings)

        token = service.create_access_token(user_id="test-user")
        payload = service.decode_access_token(token)

        assert payload["sub"] == "test-user"
