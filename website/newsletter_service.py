"""Newsletter service for managing subscriptions."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models import NewsletterSubscriber


class NewsletterService:
    """Service for managing newsletter subscriptions."""

    def __init__(self, session: AsyncSession):
        """Initialize the newsletter service.

        Args:
            session: Database session
        """
        self.session = session

    async def subscribe(self, email: str) -> tuple[bool, str]:
        """Subscribe an email to the newsletter.

        Args:
            email: Email address to subscribe

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Check if email already exists
            existing = await self.get_subscriber(email)
            if existing:
                if existing.active:
                    return False, "This email is already subscribed to our newsletter."
                else:
                    # Reactivate subscription
                    existing.active = True
                    await self.session.commit()
                    return True, "Your subscription has been reactivated!"

            # Create new subscriber
            subscriber = NewsletterSubscriber(email=email, active=True)
            self.session.add(subscriber)
            await self.session.commit()
            return True, "Thank you for subscribing! You'll receive our monthly updates."

        except IntegrityError:
            await self.session.rollback()
            return False, "This email is already subscribed."
        except Exception as e:
            await self.session.rollback()
            return False, f"An error occurred: {str(e)}"

    async def get_subscriber(self, email: str) -> Optional[NewsletterSubscriber]:
        """Get a subscriber by email.

        Args:
            email: Email address to look up

        Returns:
            NewsletterSubscriber if found, None otherwise
        """
        stmt = select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def unsubscribe(self, email: str) -> tuple[bool, str]:
        """Unsubscribe an email from the newsletter.

        Args:
            email: Email address to unsubscribe

        Returns:
            Tuple of (success: bool, message: str)
        """
        subscriber = await self.get_subscriber(email)
        if not subscriber:
            return False, "Email not found in our newsletter list."

        if not subscriber.active:
            return False, "This email is already unsubscribed."

        subscriber.active = False
        await self.session.commit()
        return True, "You have been unsubscribed from our newsletter."
