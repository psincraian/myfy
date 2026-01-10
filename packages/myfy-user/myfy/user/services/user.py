"""
User service for CRUD operations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from myfy.user.errors import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from myfy.user.models.token import EmailVerificationToken, PasswordResetToken

if TYPE_CHECKING:
    from myfy.user.auth.password import PasswordHasher
    from myfy.user.config import UserSettings
    from myfy.user.models.base import BaseUser

# Type variable for user model
T = TypeVar("T", bound="BaseUser")


class UserService(Generic[T]):
    """
    Service for user management operations.

    Provides CRUD operations for users and related entities.

    Usage:
        ```python
        # Injected via DI
        async def create_user(user_service: UserService) -> dict:
            user = await user_service.create(
                email="user@example.com",
                password="secretpass",
            )
            return {"id": user.id, "email": user.email}
        ```
    """

    def __init__(
        self,
        session: AsyncSession,
        user_model: type[T],
        password_hasher: PasswordHasher,
        settings: UserSettings,
    ) -> None:
        """
        Initialize user service.

        Args:
            session: Database session (REQUEST-scoped)
            user_model: User model class
            password_hasher: Password hasher instance
            settings: User settings
        """
        self._session = session
        self._user_model = user_model
        self._hasher = password_hasher
        self._settings = settings

    async def create(
        self,
        email: str,
        password: str | None = None,
        is_superuser: bool = False,
        email_verified: bool = False,
        **extra_fields: Any,
    ) -> T:
        """
        Create a new user.

        Args:
            email: User's email address
            password: Optional password (hashed before storage)
            is_superuser: Whether user is an admin
            email_verified: Whether email is verified
            **extra_fields: Additional fields for custom User model

        Returns:
            Created user instance

        Raises:
            UserAlreadyExistsError: If email is already registered
            PasswordTooWeakError: If password doesn't meet requirements
        """
        # Check if email already exists
        existing = await self.get_by_email(email)
        if existing:
            raise UserAlreadyExistsError(email)

        # Create user instance
        user = self._user_model(
            email=email.lower().strip(),
            is_superuser=is_superuser,
            email_verified=email_verified,
            **extra_fields,
        )

        # Hash password if provided
        if password:
            user.password_hash = self._hasher.hash(password)

        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def get_by_id(self, user_id: str) -> T | None:
        """
        Get user by ID.

        Args:
            user_id: User's ID

        Returns:
            User instance or None if not found
        """
        result = await self._session.execute(
            select(self._user_model).where(self._user_model.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> T | None:
        """
        Get user by email.

        Args:
            email: User's email address

        Returns:
            User instance or None if not found
        """
        result = await self._session.execute(
            select(self._user_model).where(self._user_model.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def authenticate(self, email: str, password: str) -> T:
        """
        Authenticate user with email and password.

        Args:
            email: User's email address
            password: Password to verify

        Returns:
            Authenticated user instance

        Raises:
            InvalidCredentialsError: If credentials are invalid
        """
        user = await self.get_by_email(email)
        if not user:
            raise InvalidCredentialsError

        if not user.password_hash:
            raise InvalidCredentialsError

        if not self._hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError

        if not user.is_active:
            raise InvalidCredentialsError

        return user

    async def update(self, user_id: str, **fields: Any) -> T | None:
        """
        Update user fields.

        Args:
            user_id: User's ID
            **fields: Fields to update

        Returns:
            Updated user or None if not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        for key, value in fields.items():
            if hasattr(user, key):
                setattr(user, key, value)

        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def set_password(self, user_id: str, new_password: str) -> None:
        """
        Set user's password.

        Args:
            user_id: User's ID
            new_password: New password to set

        Raises:
            UserNotFoundError: If user not found
            PasswordTooWeakError: If password doesn't meet requirements
        """
        user = await self.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)

        user.password_hash = self._hasher.hash(new_password)
        await self._session.commit()

        # Invalidate all password reset tokens
        await self._invalidate_password_reset_tokens(user_id)

    async def verify_email(self, user_id: str) -> None:
        """
        Mark user's email as verified.

        Args:
            user_id: User's ID

        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)

        user.email_verified = True
        await self._session.commit()

    async def update_last_login(self, user_id: str) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: User's ID
        """
        user = await self.get_by_id(user_id)
        if user:
            user.last_login = datetime.now(UTC)
            await self._session.commit()

    async def deactivate(self, user_id: str) -> None:
        """
        Deactivate user account.

        Args:
            user_id: User's ID

        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)

        user.is_active = False
        await self._session.commit()

    async def activate(self, user_id: str) -> None:
        """
        Activate user account.

        Args:
            user_id: User's ID

        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)

        user.is_active = True
        await self._session.commit()

    async def delete(self, user_id: str) -> None:
        """
        Delete user account.

        Args:
            user_id: User's ID

        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)

        await self._session.delete(user)
        await self._session.commit()

    async def list_users(
        self,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = False,
    ) -> list[T]:
        """
        List users with pagination.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            active_only: If True, only return active users

        Returns:
            List of users
        """
        query = select(self._user_model)

        if active_only:
            query = query.where(self._user_model.is_active == True)  # noqa: E712

        query = query.order_by(self._user_model.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_admins(self, limit: int = 50) -> list[T]:
        """
        List admin users.

        Args:
            limit: Maximum number of users to return

        Returns:
            List of admin users
        """
        result = await self._session.execute(
            select(self._user_model)
            .where(self._user_model.is_superuser == True)  # noqa: E712
            .order_by(self._user_model.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_users(self, active_only: bool = False) -> int:
        """
        Count users.

        Args:
            active_only: If True, only count active users

        Returns:
            Number of users
        """
        from sqlalchemy import func

        query = select(func.count(self._user_model.id))

        if active_only:
            query = query.where(self._user_model.is_active == True)  # noqa: E712

        result = await self._session.execute(query)
        return result.scalar() or 0

    # Token management

    async def create_verification_token(self, user_id: str) -> str:
        """
        Create email verification token.

        Args:
            user_id: User's ID

        Returns:
            Token string

        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)

        token = EmailVerificationToken.create(
            user_id=user_id,
            expires_in_seconds=self._settings.email_verification_lifetime,
        )
        self._session.add(token)
        await self._session.commit()
        return token.token

    async def verify_email_token(self, token: str) -> T:
        """
        Verify email using token.

        Args:
            token: Verification token

        Returns:
            Verified user

        Raises:
            TokenInvalidError: If token is invalid
            TokenExpiredError: If token is expired
        """
        from myfy.user.errors import TokenExpiredError, TokenInvalidError

        result = await self._session.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.token == token)
        )
        token_obj = result.scalar_one_or_none()

        if not token_obj:
            raise TokenInvalidError("verification")

        if token_obj.is_expired:
            raise TokenExpiredError("verification")

        if token_obj.is_used:
            raise TokenInvalidError("verification")

        # Mark token as used
        token_obj.mark_used()

        # Verify user's email
        user = await self.get_by_id(token_obj.user_id)
        if not user:
            raise TokenInvalidError("verification")

        user.email_verified = True
        await self._session.commit()
        return user

    async def create_password_reset_token(self, email: str) -> str | None:
        """
        Create password reset token.

        Args:
            email: User's email

        Returns:
            Token string or None if user not found
        """
        user = await self.get_by_email(email)
        if not user:
            return None

        # Invalidate existing tokens
        await self._invalidate_password_reset_tokens(user.id)

        token = PasswordResetToken.create(
            user_id=user.id,
            expires_in_seconds=self._settings.password_reset_lifetime,
        )
        self._session.add(token)
        await self._session.commit()
        return token.token

    async def reset_password_with_token(self, token: str, new_password: str) -> T:
        """
        Reset password using token.

        Args:
            token: Reset token
            new_password: New password

        Returns:
            User with updated password

        Raises:
            TokenInvalidError: If token is invalid
            TokenExpiredError: If token is expired
        """
        from myfy.user.errors import TokenExpiredError, TokenInvalidError

        result = await self._session.execute(
            select(PasswordResetToken).where(PasswordResetToken.token == token)
        )
        token_obj = result.scalar_one_or_none()

        if not token_obj:
            raise TokenInvalidError("password reset")

        if not token_obj.is_valid:
            if token_obj.is_expired:
                raise TokenExpiredError("password reset")
            raise TokenInvalidError("password reset")

        # Mark token as used
        token_obj.mark_used()

        # Update password
        user = await self.get_by_id(token_obj.user_id)
        if not user:
            raise TokenInvalidError("password reset")

        user.password_hash = self._hasher.hash(new_password)
        await self._session.commit()
        return user

    async def _invalidate_password_reset_tokens(self, user_id: str) -> None:
        """Invalidate all password reset tokens for a user."""
        result = await self._session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.invalidated == False,  # noqa: E712
                PasswordResetToken.used_at.is_(None),
            )
        )
        tokens = result.scalars().all()
        for token in tokens:
            token.invalidate()

    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired tokens.

        Returns:
            Number of tokens deleted
        """
        from sqlalchemy import delete

        now = datetime.now(UTC)
        count = 0

        # Delete expired verification tokens
        result = await self._session.execute(
            delete(EmailVerificationToken).where(EmailVerificationToken.expires_at < now)
        )
        count += getattr(result, "rowcount", 0) or 0

        # Delete expired/used password reset tokens
        result = await self._session.execute(
            delete(PasswordResetToken).where(
                (PasswordResetToken.expires_at < now)
                | (PasswordResetToken.used_at.isnot(None))
                | (PasswordResetToken.invalidated == True)  # noqa: E712
            )
        )
        count += getattr(result, "rowcount", 0) or 0

        await self._session.commit()
        return count
