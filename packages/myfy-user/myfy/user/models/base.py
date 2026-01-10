"""
Base user model with subclassable design.

Provides abstract BaseUser that can be extended with custom fields.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from myfy.data import Base

if TYPE_CHECKING:
    from .oauth import OAuthConnection
    from .token import EmailVerificationToken, PasswordResetToken


class BaseUser(Base):
    """
    Abstract base class for User models.

    Extend this class to add custom fields to your user model:

    ```python
    from myfy.user import BaseUser
    from sqlalchemy import String, ForeignKey
    from sqlalchemy.orm import Mapped, mapped_column, relationship

    class User(BaseUser):
        __tablename__ = "users"

        # Custom fields
        full_name: Mapped[str | None] = mapped_column(String(255))
        phone: Mapped[str | None] = mapped_column(String(20))
        avatar_url: Mapped[str | None] = mapped_column(Text)

        # Custom relationships
        organization_id: Mapped[str | None] = mapped_column(ForeignKey("orgs.id"))
        organization: Mapped["Organization"] = relationship(back_populates="members")
    ```

    The base class provides:
    - id: UUID primary key
    - email: Unique email address (indexed)
    - email_verified: Boolean flag
    - password_hash: Hashed password (nullable for OAuth-only users)
    - is_active: Account enabled flag
    - is_superuser: Admin flag
    - display_name: Optional display name
    - created_at, updated_at: Timestamps
    - last_login: Last login timestamp
    - oauth_connections: Relationship to OAuth accounts
    - email_verification_tokens: Relationship to verification tokens
    - password_reset_tokens: Relationship to password reset tokens
    """

    __abstract__ = True

    # Primary key - UUID string
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Email - unique and indexed
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    # Email verification status
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Password hash - nullable for OAuth-only users
    password_hash: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Superuser flag for admin access
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Display name for UI
    display_name: Mapped[str | None] = mapped_column(
        String(255),
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

    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # OAuth connections relationship
    @declared_attr
    def oauth_connections(cls) -> Mapped[list[OAuthConnection]]:  # noqa: N805
        return relationship(
            "OAuthConnection",
            back_populates="user",
            cascade="all, delete-orphan",
            lazy="selectin",
        )

    # Email verification tokens relationship
    @declared_attr
    def email_verification_tokens(cls) -> Mapped[list[EmailVerificationToken]]:  # noqa: N805
        return relationship(
            "EmailVerificationToken",
            back_populates="user",
            cascade="all, delete-orphan",
            lazy="selectin",
        )

    # Password reset tokens relationship
    @declared_attr
    def password_reset_tokens(cls) -> Mapped[list[PasswordResetToken]]:  # noqa: N805
        return relationship(
            "PasswordResetToken",
            back_populates="user",
            cascade="all, delete-orphan",
            lazy="selectin",
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id!r}, email={self.email!r})>"

    def has_password(self) -> bool:
        """Check if user has a password set."""
        return self.password_hash is not None

    def has_oauth(self, provider: str | None = None) -> bool:
        """Check if user has OAuth connection(s)."""
        if provider is None:
            return len(self.oauth_connections) > 0
        return any(c.provider == provider for c in self.oauth_connections)


class DefaultUser(BaseUser):
    """
    Default User model for applications that don't need customization.

    Use this directly if you don't need custom fields, or extend
    BaseUser for more control.

    Example:
        ```python
        from myfy.user import UserModule, DefaultUser

        app.add_module(UserModule(user_model=DefaultUser))
        ```
    """

    __tablename__ = "users"
