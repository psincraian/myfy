"""
Token models for email verification and password reset.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from myfy.data import Base

if TYPE_CHECKING:
    from .base import BaseUser


class EmailVerificationToken(Base):
    """
    Token for email verification.

    Sent to users after registration to verify their email address.
    """

    __tablename__ = "email_verification_tokens"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Token value - URL-safe random string
    token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )

    # Expiration
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Usage tracking
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship back to user
    # Use string reference to the concrete class that maps to 'users' table
    user: Mapped[BaseUser] = relationship(
        "DefaultUser",
        back_populates="email_verification_tokens",
        foreign_keys=[user_id],
    )

    def __repr__(self) -> str:
        return f"<EmailVerificationToken(id={self.id!r}, user_id={self.user_id!r})>"

    @classmethod
    def create(
        cls,
        user_id: str,
        expires_in_seconds: int = 86400,  # 24 hours
    ) -> EmailVerificationToken:
        """
        Create a new verification token.

        Args:
            user_id: The user's ID
            expires_in_seconds: Token lifetime in seconds (default: 24 hours)

        Returns:
            New EmailVerificationToken instance
        """
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in_seconds),
        )

    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.now(UTC) > self.expires_at.replace(tzinfo=UTC)

    @property
    def is_used(self) -> bool:
        """Check if token has been used."""
        return self.used_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not used)."""
        return not self.is_expired and not self.is_used

    def mark_used(self) -> None:
        """Mark token as used."""
        self.used_at = datetime.now(UTC)


class PasswordResetToken(Base):
    """
    Token for password reset.

    Sent to users when they request a password reset.
    """

    __tablename__ = "password_reset_tokens"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Token value - URL-safe random string
    token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )

    # Expiration
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Usage tracking
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Invalidation flag (e.g., when password is changed through other means)
    invalidated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship back to user
    # Use string reference to the concrete class that maps to 'users' table
    user: Mapped[BaseUser] = relationship(
        "DefaultUser",
        back_populates="password_reset_tokens",
        foreign_keys=[user_id],
    )

    def __repr__(self) -> str:
        return f"<PasswordResetToken(id={self.id!r}, user_id={self.user_id!r})>"

    @classmethod
    def create(
        cls,
        user_id: str,
        expires_in_seconds: int = 3600,  # 1 hour
    ) -> PasswordResetToken:
        """
        Create a new password reset token.

        Args:
            user_id: The user's ID
            expires_in_seconds: Token lifetime in seconds (default: 1 hour)

        Returns:
            New PasswordResetToken instance
        """
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in_seconds),
        )

    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.now(UTC) > self.expires_at.replace(tzinfo=UTC)

    @property
    def is_used(self) -> bool:
        """Check if token has been used."""
        return self.used_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not expired, not used, not invalidated)."""
        return not self.is_expired and not self.is_used and not self.invalidated

    def mark_used(self) -> None:
        """Mark token as used."""
        self.used_at = datetime.now(UTC)

    def invalidate(self) -> None:
        """Invalidate the token."""
        self.invalidated = True
