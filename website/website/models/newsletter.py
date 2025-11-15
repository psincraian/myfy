"""Newsletter subscriber model."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class NewsletterSubscriber(Base):
    """Newsletter subscriber model.

    Attributes:
        id: Primary key
        email: Subscriber email address (unique, indexed)
        subscribed_at: Timestamp when subscription was created
        active: Whether subscription is active
    """

    __tablename__ = "newsletter_subscribers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    subscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        """String representation of the subscriber."""
        return f"<NewsletterSubscriber(email={self.email}, active={self.active})>"
