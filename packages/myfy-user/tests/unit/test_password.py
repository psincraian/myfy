"""Unit tests for PasswordHasher."""

import pytest

from myfy.user.auth.password import PasswordHasher
from myfy.user.errors import PasswordTooWeakError


class TestPasswordHasher:
    """Tests for PasswordHasher class."""

    def test_hash_password_argon2(self):
        """Test password hashing with argon2."""
        hasher = PasswordHasher(algorithm="argon2", min_length=8)
        password = "securepassword123"

        hashed = hasher.hash(password)

        assert hashed != password
        assert hashed.startswith("$argon2")
        assert len(hashed) > 50

    def test_verify_password_correct(self, password_hasher):
        """Test verifying correct password."""
        password = "correctpassword"
        hashed = password_hasher.hash(password)

        assert password_hasher.verify(password, hashed) is True

    def test_verify_password_incorrect(self, password_hasher):
        """Test verifying incorrect password."""
        password = "correctpassword"
        hashed = password_hasher.hash(password)

        assert password_hasher.verify("wrongpassword", hashed) is False

    def test_verify_password_empty_hash(self, password_hasher):
        """Test verifying against empty hash."""
        assert password_hasher.verify("password", "") is False

    def test_verify_password_invalid_hash(self, password_hasher):
        """Test verifying against invalid hash."""
        assert password_hasher.verify("password", "not-a-valid-hash") is False

    def test_hash_different_each_time(self, password_hasher):
        """Test that hashing same password produces different hashes (due to salt)."""
        password = "samepassword"

        hash1 = password_hasher.hash(password)
        hash2 = password_hasher.hash(password)

        assert hash1 != hash2
        # But both should verify
        assert password_hasher.verify(password, hash1) is True
        assert password_hasher.verify(password, hash2) is True

    def test_validate_password_too_short(self, password_hasher):
        """Test password validation - too short."""
        with pytest.raises(PasswordTooWeakError) as exc_info:
            password_hasher.validate_password("short")

        assert "at least 8 characters" in str(exc_info.value)

    def test_validate_password_minimum_length(self, password_hasher):
        """Test password validation with minimum length."""
        # Should not raise for exactly 8 characters
        password_hasher.validate_password("12345678")

    def test_validate_password_long_password(self, password_hasher):
        """Test password validation with long password."""
        password_hasher.validate_password("this-is-a-very-long-password-123")

    def test_custom_min_length(self):
        """Test custom minimum password length."""
        hasher = PasswordHasher(algorithm="argon2", min_length=12)

        # 8 chars should fail with min_length=12
        with pytest.raises(PasswordTooWeakError):
            hasher.validate_password("12345678")

        # 12 chars should pass
        hasher.validate_password("123456789012")

    def test_needs_rehash_same_algorithm(self, password_hasher):
        """Test needs_rehash returns False for current algorithm."""
        hashed = password_hasher.hash("password")
        assert password_hasher.needs_rehash(hashed) is False

    def test_hash_empty_password(self, password_hasher):
        """Test hashing empty password (should fail validation)."""
        with pytest.raises(PasswordTooWeakError):
            password_hasher.validate_password("")


class TestPasswordHasherAlgorithmDetection:
    """Tests for algorithm detection in password hashes."""

    def test_detect_argon2_hash(self):
        """Test detection of argon2 hash."""
        hasher = PasswordHasher(algorithm="argon2", min_length=8)
        hashed = hasher.hash("password")

        # Argon2 hashes start with $argon2
        assert hashed.startswith("$argon2")


class TestPasswordHasherFromSettings:
    """Tests for creating hasher from settings."""

    def test_from_settings(self, user_settings):
        """Test creating PasswordHasher from UserSettings."""
        hasher = PasswordHasher.from_settings(user_settings)

        assert hasher._algorithm == user_settings.password_algorithm
        assert hasher._min_length == user_settings.password_min_length

    def test_from_settings_hashes_correctly(self, user_settings):
        """Test that hasher from settings works correctly."""
        hasher = PasswordHasher.from_settings(user_settings)
        password = "securepassword123"

        hashed = hasher.hash(password)
        assert hasher.verify(password, hashed) is True
