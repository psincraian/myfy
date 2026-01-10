"""
User models for myfy.

Provides subclassable BaseUser model and related token/OAuth models.

Usage:
    from myfy.user.models import BaseUser

    class User(BaseUser):
        __tablename__ = "users"

        # Add custom fields
        full_name: Mapped[str | None] = mapped_column(String(255))
        phone: Mapped[str | None] = mapped_column(String(20))
"""

from .base import BaseUser, DefaultUser
from .oauth import OAuthConnection
from .token import EmailVerificationToken, PasswordResetToken

__all__ = [
    "BaseUser",
    "DefaultUser",
    "EmailVerificationToken",
    "OAuthConnection",
    "PasswordResetToken",
]
