"""Newsletter subscription service."""

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from myfy.core import SINGLETON, provider

from ..models import NewsletterSubscriber

logger = logging.getLogger(__name__)


class NewsletterService:
    """Service for managing newsletter subscriptions.

    This service handles all business logic related to newsletter subscriptions,
    including subscribing, unsubscribing, and querying subscribers.

    Args:
        session_maker: SQLAlchemy async session maker (injected via DI)
    """

    def __init__(self, session_maker: async_sessionmaker):
        """Initialize the newsletter service.

        Args:
            session_maker: Database session maker from DI container
        """
        self.session_maker = session_maker

    async def subscribe(self, email: str) -> tuple[bool, str]:
        """Subscribe an email to the newsletter.

        Args:
            email: Email address to subscribe (should be validated before calling)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            async with (
                self.session_maker() as session,
                session.begin_nested(),
            ):
                # Check if email already exists
                existing = await self._get_subscriber(session, email)
                if existing:
                    if existing.active:
                        return (
                            False,
                            "This email is already subscribed to our newsletter.",
                        )
                    # Reactivate subscription
                    existing.active = True
                    await session.commit()
                    return True, "Your subscription has been reactivated!"

                # Create new subscriber
                subscriber = NewsletterSubscriber(email=email, active=True)
                session.add(subscriber)
                await session.commit()
            return (
                True,
                "Thank you for subscribing! You'll receive our monthly updates.",
            )

        except IntegrityError as e:
            logger.warning(f"Newsletter subscription failed for {email}: {e}")
            return False, "This email is already subscribed."
        except Exception as e:
            # Log detailed error but show generic message to user
            logger.error(f"Newsletter subscription error for {email}: {e}", exc_info=True)
            return False, "An error occurred. Please try again later."

    async def unsubscribe(self, email: str) -> tuple[bool, str]:
        """Unsubscribe an email from the newsletter.

        Args:
            email: Email address to unsubscribe

        Returns:
            Tuple of (success: bool, message: str)
        """
        async with self.session_maker() as session:
            subscriber = await self._get_subscriber(session, email)
            if not subscriber:
                return False, "Email not found in our newsletter list."

            if not subscriber.active:
                return False, "This email is already unsubscribed."

            subscriber.active = False
            await session.commit()
            return True, "You have been unsubscribed from our newsletter."

    async def get_subscriber(self, email: str) -> NewsletterSubscriber | None:
        """Get a subscriber by email.

        Args:
            email: Email address to look up

        Returns:
            NewsletterSubscriber if found, None otherwise
        """
        async with self.session_maker() as session:
            return await self._get_subscriber(session, email)

    async def _get_subscriber(
        self, session: AsyncSession, email: str
    ) -> NewsletterSubscriber | None:
        """Get a subscriber by email (internal helper).

        Args:
            session: Database session
            email: Email address to look up

        Returns:
            NewsletterSubscriber if found, None otherwise
        """
        stmt = select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


@provider(scope=SINGLETON)
def newsletter_service(session_maker: async_sessionmaker) -> NewsletterService:
    """Provider for NewsletterService.

    This function is registered in the DI container and creates a singleton
    instance of NewsletterService with the injected session maker.

    Args:
        session_maker: Async session maker (automatically injected by DI)

    Returns:
        NewsletterService instance
    """
    return NewsletterService(session_maker)
