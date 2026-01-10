"""
Password hashing service with argon2 and bcrypt support.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from myfy.user.errors import PasswordTooWeakError

if TYPE_CHECKING:
    from myfy.user.config import UserSettings


class PasswordHasher:
    """
    Password hashing service.

    Supports argon2 (recommended) and bcrypt algorithms.

    Usage:
        ```python
        hasher = PasswordHasher(algorithm="argon2")

        # Hash a password
        hashed = hasher.hash("my-password")

        # Verify a password
        if hasher.verify("my-password", hashed):
            print("Password matches!")
        ```
    """

    def __init__(
        self,
        algorithm: str = "argon2",
        min_length: int = 8,
        require_uppercase: bool = False,
        require_lowercase: bool = False,
        require_digit: bool = False,
        require_special: bool = False,
    ) -> None:
        """
        Initialize password hasher.

        Args:
            algorithm: Hashing algorithm (argon2 or bcrypt)
            min_length: Minimum password length
            require_uppercase: Require at least one uppercase letter
            require_lowercase: Require at least one lowercase letter
            require_digit: Require at least one digit
            require_special: Require at least one special character
        """
        self._algorithm = algorithm
        self._min_length = min_length
        self._require_uppercase = require_uppercase
        self._require_lowercase = require_lowercase
        self._require_digit = require_digit
        self._require_special = require_special

        # Initialize the hasher based on algorithm
        if algorithm == "argon2":
            from argon2 import PasswordHasher as Argon2Hasher

            self._hasher = Argon2Hasher()
        elif algorithm == "bcrypt":
            try:
                import bcrypt  # noqa: F401

                self._hasher = None  # bcrypt uses module functions
            except ImportError as e:
                msg = (
                    "bcrypt is required for bcrypt algorithm. "
                    "Install with: pip install myfy-user[bcrypt]"
                )
                raise ImportError(msg) from e
        else:
            msg = f"Unsupported algorithm: {algorithm}"
            raise ValueError(msg)

    @classmethod
    def from_settings(cls, settings: UserSettings) -> PasswordHasher:
        """Create hasher from UserSettings."""
        return cls(
            algorithm=settings.password_algorithm,
            min_length=settings.password_min_length,
            require_uppercase=settings.password_require_uppercase,
            require_lowercase=settings.password_require_lowercase,
            require_digit=settings.password_require_digit,
            require_special=settings.password_require_special,
        )

    def validate_password(self, password: str) -> None:
        """
        Validate password meets requirements.

        Args:
            password: Password to validate

        Raises:
            PasswordTooWeakError: If password doesn't meet requirements
        """
        if len(password) < self._min_length:
            raise PasswordTooWeakError(
                f"Password must be at least {self._min_length} characters"
            )

        if self._require_uppercase and not re.search(r"[A-Z]", password):
            raise PasswordTooWeakError("Password must contain at least one uppercase letter")

        if self._require_lowercase and not re.search(r"[a-z]", password):
            raise PasswordTooWeakError("Password must contain at least one lowercase letter")

        if self._require_digit and not re.search(r"\d", password):
            raise PasswordTooWeakError("Password must contain at least one digit")

        if self._require_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise PasswordTooWeakError("Password must contain at least one special character")

    def hash(self, password: str, validate: bool = True) -> str:
        """
        Hash a password.

        Args:
            password: Plain text password to hash
            validate: Whether to validate password strength first

        Returns:
            Hashed password string

        Raises:
            PasswordTooWeakError: If validate=True and password is too weak
        """
        if validate:
            self.validate_password(password)

        if self._algorithm == "argon2":
            assert self._hasher is not None
            return self._hasher.hash(password)
        # bcrypt
        import bcrypt

        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify(self, password: str, hashed: str) -> bool:
        """
        Verify a password against a hash.

        Args:
            password: Plain text password to verify
            hashed: Hashed password to compare against

        Returns:
            True if password matches, False otherwise
        """
        try:
            if self._algorithm == "argon2":
                assert self._hasher is not None
                self._hasher.verify(hashed, password)
                return True
            # bcrypt
            import bcrypt

            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    def needs_rehash(self, hashed: str) -> bool:
        """
        Check if a hash needs to be rehashed (e.g., due to parameter changes).

        Args:
            hashed: Hashed password to check

        Returns:
            True if hash should be regenerated, False otherwise
        """
        if self._algorithm == "argon2":
            assert self._hasher is not None
            return self._hasher.check_needs_rehash(hashed)
        # bcrypt doesn't have a native needs_rehash, so we don't rehash
        return False
