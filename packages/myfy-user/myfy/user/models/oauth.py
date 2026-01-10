"""
OAuth connection model for storing provider links.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from myfy.data import Base

if TYPE_CHECKING:
    from .base import BaseUser


def _get_user_class() -> type:
    """
    Get the concrete user class for relationship resolution.

    This is called at relationship configuration time to resolve
    the 'users' table to the appropriate model class.
    """
    # Import here to avoid circular imports and get the actual registered class
    from myfy.user.models.base import DefaultUser

    return DefaultUser


class OAuthConnection(Base):
    """
    OAuth provider connection for a user.

    Links a user account to an OAuth provider (Google, GitHub, etc.).
    Each user can have multiple OAuth connections (one per provider).
    """

    __tablename__ = "oauth_connections"

    # Constraints to ensure:
    # 1. One connection per provider per user
    # 2. One user per provider account (prevent account hijacking)
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
    )

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

    # Provider identification
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    provider_user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # OAuth tokens (should be encrypted in production)
    access_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    refresh_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Provider profile data (cached for display)
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship back to user
    # Use string reference to the concrete class that maps to 'users' table
    user: Mapped[BaseUser] = relationship(
        "DefaultUser",
        back_populates="oauth_connections",
        foreign_keys=[user_id],
    )

    def __repr__(self) -> str:
        return (
            f"<OAuthConnection(id={self.id!r}, provider={self.provider!r}, "
            f"user_id={self.user_id!r})>"
        )

    def is_token_expired(self) -> bool:
        """Check if the access token is expired."""
        if self.token_expires_at is None:
            return False
        return datetime.now(self.token_expires_at.tzinfo) > self.token_expires_at
