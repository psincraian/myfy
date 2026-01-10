"""
Background tasks for user management.

Provides async tasks for email sending and token cleanup.
These tasks integrate with myfy-tasks module when available.

Usage:
    ```python
    from myfy.user.tasks import send_verification_email, send_password_reset_email

    # Dispatch verification email
    await send_verification_email.send(user_id=user.id, token=token.token)

    # Dispatch password reset email
    await send_password_reset_email.send(user_id=user.id, token=token.token)
    ```

Note:
    These tasks require an EmailService implementation to be registered
    in the DI container. The default NullEmailService logs emails but
    doesn't send them - you must provide your own implementation.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

# Try to import tasks module - it's optional
try:
    from myfy.tasks import TaskContext, task

    HAS_TASKS = True
except ImportError:
    HAS_TASKS = False

    # Provide stub decorator when tasks module is not available
    def task(func=None, **kwargs):  # type: ignore[no-untyped-def]  # noqa: ARG001
        """Stub task decorator when myfy-tasks is not installed."""
        if func is not None:
            return func

        def decorator(f):  # type: ignore[no-untyped-def]
            return f

        return decorator

    class TaskContext:  # type: ignore[no-redef]
        """Stub TaskContext when myfy-tasks is not installed."""


logger = logging.getLogger(__name__)


@task(name="user.send_verification_email", max_retries=3)
async def send_verification_email(
    user_id: str,
    token: str,
    base_url: str = "",
) -> bool:
    """
    Send email verification email to user.

    Args:
        user_id: The user's ID
        token: The verification token
        base_url: Base URL for verification link

    Returns:
        True if email was sent successfully
    """
    # Import here to avoid circular imports and allow DI
    from myfy.core.container import get_current_container

    container = get_current_container()
    if container is None:
        logger.error("No container available for send_verification_email task")
        return False

    try:
        from myfy.user.services.email import EmailService
        from myfy.user.services.user import UserService

        user_service = container.get(UserService)
        email_service = container.get(EmailService)

        user = await user_service.get_by_id(user_id)
        if not user:
            logger.warning(f"User not found for verification email: {user_id}")
            return False

        # Build verification URL
        verify_url = f"{base_url}/verify-email/{token}"

        # Send email
        await email_service.send_verification_email(
            to_email=user.email,
            verify_url=verify_url,
            user_name=getattr(user, "display_name", None) or user.email,
        )

        logger.info(f"Verification email sent to {user.email}")
        return True

    except Exception as e:
        logger.exception(f"Failed to send verification email: {e}")
        raise


@task(name="user.send_password_reset_email", max_retries=3)
async def send_password_reset_email(
    user_id: str,
    token: str,
    base_url: str = "",
) -> bool:
    """
    Send password reset email to user.

    Args:
        user_id: The user's ID
        token: The password reset token
        base_url: Base URL for reset link

    Returns:
        True if email was sent successfully
    """
    from myfy.core.container import get_current_container

    container = get_current_container()
    if container is None:
        logger.error("No container available for send_password_reset_email task")
        return False

    try:
        from myfy.user.services.email import EmailService
        from myfy.user.services.user import UserService

        user_service = container.get(UserService)
        email_service = container.get(EmailService)

        user = await user_service.get_by_id(user_id)
        if not user:
            logger.warning(f"User not found for password reset email: {user_id}")
            return False

        # Build reset URL
        reset_url = f"{base_url}/reset-password/{token}"

        # Send email
        await email_service.send_password_reset_email(
            to_email=user.email,
            reset_url=reset_url,
            user_name=getattr(user, "display_name", None) or user.email,
        )

        logger.info(f"Password reset email sent to {user.email}")
        return True

    except Exception as e:
        logger.exception(f"Failed to send password reset email: {e}")
        raise


@task(name="user.send_welcome_email", max_retries=3)
async def send_welcome_email(
    user_id: str,
    base_url: str = "",
) -> bool:
    """
    Send welcome email to newly registered user.

    Args:
        user_id: The user's ID
        base_url: Base URL for the application

    Returns:
        True if email was sent successfully
    """
    from myfy.core.container import get_current_container

    container = get_current_container()
    if container is None:
        logger.error("No container available for send_welcome_email task")
        return False

    try:
        from myfy.user.services.email import EmailService
        from myfy.user.services.user import UserService

        user_service = container.get(UserService)
        email_service = container.get(EmailService)

        user = await user_service.get_by_id(user_id)
        if not user:
            logger.warning(f"User not found for welcome email: {user_id}")
            return False

        # Send email
        await email_service.send_welcome_email(
            to_email=user.email,
            user_name=getattr(user, "display_name", None) or user.email,
            login_url=f"{base_url}/login",
        )

        logger.info(f"Welcome email sent to {user.email}")
        return True

    except Exception as e:
        logger.exception(f"Failed to send welcome email: {e}")
        raise


@task(name="user.cleanup_expired_tokens")
async def cleanup_expired_tokens(
    days_old: int = 7,
) -> dict[str, int]:
    """
    Clean up expired verification and password reset tokens.

    This task should be run periodically (e.g., daily) to remove
    old tokens from the database.

    Args:
        days_old: Delete tokens older than this many days

    Returns:
        Dictionary with counts of deleted tokens by type
    """
    from myfy.core.container import get_current_container

    container = get_current_container()
    if container is None:
        logger.error("No container available for cleanup_expired_tokens task")
        return {"verification": 0, "password_reset": 0}

    try:
        from sqlalchemy import delete
        from sqlalchemy.ext.asyncio import AsyncSession

        from myfy.user.models.token import EmailVerificationToken, PasswordResetToken

        session = container.get(AsyncSession)
        cutoff_date = datetime.now(UTC) - timedelta(days=days_old)

        # Delete expired verification tokens
        verification_result = await session.execute(
            delete(EmailVerificationToken).where(EmailVerificationToken.expires_at < cutoff_date)
        )
        verification_count = verification_result.rowcount

        # Delete expired password reset tokens
        reset_result = await session.execute(
            delete(PasswordResetToken).where(PasswordResetToken.expires_at < cutoff_date)
        )
        reset_count = reset_result.rowcount

        await session.commit()

        logger.info(
            f"Cleaned up tokens: {verification_count} verification, {reset_count} password reset"
        )

        return {
            "verification": verification_count,
            "password_reset": reset_count,
        }

    except Exception as e:
        logger.exception(f"Failed to cleanup expired tokens: {e}")
        raise


@task(name="user.cleanup_inactive_users")
async def cleanup_inactive_users(
    days_inactive: int = 365,
    unverified_only: bool = True,
) -> int:
    """
    Clean up users who have been inactive for a long time.

    By default, only removes users who never verified their email.
    This helps clean up abandoned registrations.

    Args:
        days_inactive: Delete users inactive for this many days
        unverified_only: Only delete users with unverified emails

    Returns:
        Number of users deleted
    """
    from myfy.core.container import get_current_container

    container = get_current_container()
    if container is None:
        logger.error("No container available for cleanup_inactive_users task")
        return 0

    try:
        from sqlalchemy import and_, delete
        from sqlalchemy.ext.asyncio import AsyncSession

        from myfy.user.models.base import BaseUser

        session = container.get(AsyncSession)
        cutoff_date = datetime.now(UTC) - timedelta(days=days_inactive)

        # Build delete conditions
        conditions = [BaseUser.created_at < cutoff_date]

        if unverified_only:
            conditions.append(BaseUser.email_verified == False)  # noqa: E712

        # Delete inactive users
        result = await session.execute(delete(BaseUser).where(and_(*conditions)))
        deleted_count = result.rowcount

        await session.commit()

        logger.info(f"Cleaned up {deleted_count} inactive users")
        return deleted_count

    except Exception as e:
        logger.exception(f"Failed to cleanup inactive users: {e}")
        raise
