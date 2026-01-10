"""Integration tests for UserService with real database."""

from __future__ import annotations

import pytest

from myfy.user.errors import (
    InvalidCredentialsError,
    PasswordTooWeakError,
    TokenInvalidError,
    UserAlreadyExistsError,
    UserNotFoundError,
)


class TestUserServiceCreate:
    """Tests for UserService.create()."""

    @pytest.mark.asyncio
    async def test_create_user(self, user_service):
        """Test creating a new user."""
        user = await user_service.create(
            email="newuser@example.com",
            password="securepass123",
        )

        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.password_hash is not None
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.email_verified is False

    @pytest.mark.asyncio
    async def test_create_user_email_normalized(self, user_service):
        """Test that email is normalized (lowercase, stripped)."""
        user = await user_service.create(
            email="  TestUser@EXAMPLE.com  ",
            password="securepass123",
        )

        assert user.email == "testuser@example.com"

    @pytest.mark.asyncio
    async def test_create_superuser(self, user_service):
        """Test creating a superuser."""
        user = await user_service.create(
            email="admin@example.com",
            password="adminpass123",
            is_superuser=True,
        )

        assert user.is_superuser is True

    @pytest.mark.asyncio
    async def test_create_verified_user(self, user_service):
        """Test creating a pre-verified user."""
        user = await user_service.create(
            email="verified@example.com",
            password="password123",
            email_verified=True,
        )

        assert user.email_verified is True

    @pytest.mark.asyncio
    async def test_create_user_without_password(self, user_service):
        """Test creating OAuth-only user without password."""
        user = await user_service.create(
            email="oauth@example.com",
            password=None,
        )

        assert user.password_hash is None
        assert user.has_password() is False

    @pytest.mark.asyncio
    async def test_create_duplicate_email_raises(self, user_service):
        """Test creating user with existing email raises error."""
        await user_service.create(
            email="duplicate@example.com",
            password="password123",
        )

        with pytest.raises(UserAlreadyExistsError) as exc_info:
            await user_service.create(
                email="duplicate@example.com",
                password="different123",
            )

        assert "duplicate@example.com" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_user_weak_password_raises(self, user_service):
        """Test that weak password raises error."""
        with pytest.raises(PasswordTooWeakError):
            await user_service.create(
                email="weakpass@example.com",
                password="short",  # Less than 8 characters
            )


class TestUserServiceQuery:
    """Tests for UserService query methods."""

    @pytest.mark.asyncio
    async def test_get_by_id(self, user_service, test_user):
        """Test getting user by ID."""
        user = await user_service.get_by_id(test_user.id)

        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, user_service):
        """Test getting non-existent user by ID."""
        user = await user_service.get_by_id("non-existent-id")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_by_email(self, user_service, test_user):
        """Test getting user by email."""
        user = await user_service.get_by_email(test_user.email)

        assert user is not None
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_get_by_email_case_insensitive(self, user_service, test_user):
        """Test that email lookup is case-insensitive."""
        user = await user_service.get_by_email(test_user.email.upper())
        assert user is not None
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, user_service):
        """Test getting non-existent user by email."""
        user = await user_service.get_by_email("nonexistent@example.com")
        assert user is None


class TestUserServiceAuthentication:
    """Tests for UserService.authenticate()."""

    @pytest.mark.asyncio
    async def test_authenticate_success(self, user_service, test_user):
        """Test successful authentication."""
        user = await user_service.authenticate(
            email="test@example.com",
            password="password123",
        )

        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, user_service, test_user):
        """Test authentication with wrong password."""
        with pytest.raises(InvalidCredentialsError):
            await user_service.authenticate(
                email="test@example.com",
                password="wrongpassword",
            )

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self, user_service):
        """Test authentication with non-existent user."""
        with pytest.raises(InvalidCredentialsError):
            await user_service.authenticate(
                email="nonexistent@example.com",
                password="password123",
            )

    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self, user_service):
        """Test authentication with inactive user."""
        user = await user_service.create(
            email="inactive@example.com",
            password="password123",
        )
        await user_service.deactivate(user.id)

        with pytest.raises(InvalidCredentialsError):
            await user_service.authenticate(
                email="inactive@example.com",
                password="password123",
            )

    @pytest.mark.asyncio
    async def test_authenticate_oauth_only_user(self, user_service):
        """Test authentication with OAuth-only user (no password)."""
        await user_service.create(
            email="oauth@example.com",
            password=None,  # OAuth-only
        )

        with pytest.raises(InvalidCredentialsError):
            await user_service.authenticate(
                email="oauth@example.com",
                password="anypassword",
            )


class TestUserServiceUpdate:
    """Tests for UserService update methods."""

    @pytest.mark.asyncio
    async def test_update_user(self, user_service, test_user):
        """Test updating user fields."""
        updated = await user_service.update(
            test_user.id,
            display_name="New Display Name",
        )

        assert updated is not None
        assert updated.display_name == "New Display Name"

    @pytest.mark.asyncio
    async def test_update_nonexistent_user(self, user_service):
        """Test updating non-existent user."""
        result = await user_service.update(
            "non-existent-id",
            display_name="Test",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_set_password(self, user_service, test_user):
        """Test setting new password."""
        await user_service.set_password(test_user.id, "newpassword123")

        # Verify new password works
        user = await user_service.authenticate(
            email="test@example.com",
            password="newpassword123",
        )
        assert user.id == test_user.id

        # Verify old password doesn't work
        with pytest.raises(InvalidCredentialsError):
            await user_service.authenticate(
                email="test@example.com",
                password="password123",
            )

    @pytest.mark.asyncio
    async def test_set_password_nonexistent_user(self, user_service):
        """Test setting password for non-existent user."""
        with pytest.raises(UserNotFoundError):
            await user_service.set_password("non-existent-id", "newpass123")

    @pytest.mark.asyncio
    async def test_verify_email(self, user_service, unverified_user):
        """Test verifying user's email."""
        assert unverified_user.email_verified is False

        await user_service.verify_email(unverified_user.id)

        user = await user_service.get_by_id(unverified_user.id)
        assert user.email_verified is True

    @pytest.mark.asyncio
    async def test_update_last_login(self, user_service, test_user):
        """Test updating last login timestamp."""
        assert test_user.last_login is None

        await user_service.update_last_login(test_user.id)

        user = await user_service.get_by_id(test_user.id)
        assert user.last_login is not None


class TestUserServiceAccountStatus:
    """Tests for account activation/deactivation."""

    @pytest.mark.asyncio
    async def test_deactivate_user(self, user_service, test_user):
        """Test deactivating user account."""
        await user_service.deactivate(test_user.id)

        user = await user_service.get_by_id(test_user.id)
        assert user.is_active is False

    @pytest.mark.asyncio
    async def test_activate_user(self, user_service, test_user):
        """Test activating user account."""
        await user_service.deactivate(test_user.id)
        await user_service.activate(test_user.id)

        user = await user_service.get_by_id(test_user.id)
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_deactivate_nonexistent_user(self, user_service):
        """Test deactivating non-existent user."""
        with pytest.raises(UserNotFoundError):
            await user_service.deactivate("non-existent-id")

    @pytest.mark.asyncio
    async def test_delete_user(self, user_service, test_user):
        """Test deleting user."""
        user_id = test_user.id
        await user_service.delete(user_id)

        user = await user_service.get_by_id(user_id)
        assert user is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, user_service):
        """Test deleting non-existent user."""
        with pytest.raises(UserNotFoundError):
            await user_service.delete("non-existent-id")


class TestUserServiceList:
    """Tests for listing users."""

    @pytest.mark.asyncio
    async def test_list_users(self, user_service):
        """Test listing users."""
        # Create multiple users
        await user_service.create(email="user1@example.com", password="pass12345")
        await user_service.create(email="user2@example.com", password="pass12345")
        await user_service.create(email="user3@example.com", password="pass12345")

        users = await user_service.list_users()

        assert len(users) >= 3

    @pytest.mark.asyncio
    async def test_list_users_pagination(self, user_service):
        """Test listing users with pagination."""
        # Create multiple users
        for i in range(5):
            await user_service.create(
                email=f"paginate{i}@example.com",
                password="password123",
            )

        page1 = await user_service.list_users(limit=2, offset=0)
        page2 = await user_service.list_users(limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2
        # Different users
        assert page1[0].id != page2[0].id

    @pytest.mark.asyncio
    async def test_list_users_active_only(self, user_service):
        """Test listing only active users."""
        user1 = await user_service.create(
            email="active@example.com", password="pass12345"
        )
        user2 = await user_service.create(
            email="inactive@example.com", password="pass12345"
        )
        await user_service.deactivate(user2.id)

        active_users = await user_service.list_users(active_only=True)

        assert any(u.id == user1.id for u in active_users)
        assert not any(u.id == user2.id for u in active_users)

    @pytest.mark.asyncio
    async def test_list_admins(self, user_service, admin_user):
        """Test listing admin users."""
        admins = await user_service.list_admins()

        assert len(admins) >= 1
        assert any(a.id == admin_user.id for a in admins)
        assert all(a.is_superuser for a in admins)

    @pytest.mark.asyncio
    async def test_count_users(self, user_service):
        """Test counting users."""
        initial_count = await user_service.count_users()

        await user_service.create(email="count1@example.com", password="pass12345")
        await user_service.create(email="count2@example.com", password="pass12345")

        new_count = await user_service.count_users()
        assert new_count == initial_count + 2


class TestUserServiceEmailVerificationTokens:
    """Tests for email verification token operations."""

    @pytest.mark.asyncio
    async def test_create_verification_token(self, user_service, unverified_user):
        """Test creating verification token."""
        token = await user_service.create_verification_token(unverified_user.id)

        assert token is not None
        assert len(token) > 20  # URL-safe token

    @pytest.mark.asyncio
    async def test_verify_email_token(self, user_service, unverified_user):
        """Test verifying email with token."""
        token = await user_service.create_verification_token(unverified_user.id)

        user = await user_service.verify_email_token(token)

        assert user.id == unverified_user.id
        assert user.email_verified is True

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, user_service):
        """Test verifying with invalid token."""
        with pytest.raises(TokenInvalidError):
            await user_service.verify_email_token("invalid-token")

    @pytest.mark.asyncio
    async def test_verify_email_token_used_twice(self, user_service, unverified_user):
        """Test that token can only be used once."""
        token = await user_service.create_verification_token(unverified_user.id)

        # First use should succeed
        await user_service.verify_email_token(token)

        # Second use should fail
        with pytest.raises(TokenInvalidError):
            await user_service.verify_email_token(token)


class TestUserServicePasswordResetTokens:
    """Tests for password reset token operations."""

    @pytest.mark.asyncio
    async def test_create_password_reset_token(self, user_service, test_user):
        """Test creating password reset token."""
        token = await user_service.create_password_reset_token(test_user.email)

        assert token is not None
        assert len(token) > 20

    @pytest.mark.asyncio
    async def test_create_password_reset_token_nonexistent_email(self, user_service):
        """Test creating reset token for non-existent email returns None."""
        token = await user_service.create_password_reset_token("nonexistent@example.com")
        assert token is None

    @pytest.mark.asyncio
    async def test_reset_password_with_token(self, user_service, test_user):
        """Test resetting password with token."""
        token = await user_service.create_password_reset_token(test_user.email)

        user = await user_service.reset_password_with_token(token, "newpassword123")

        assert user.id == test_user.id

        # Verify new password works
        authenticated = await user_service.authenticate(
            email=test_user.email,
            password="newpassword123",
        )
        assert authenticated.id == test_user.id

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, user_service):
        """Test resetting password with invalid token."""
        with pytest.raises(TokenInvalidError):
            await user_service.reset_password_with_token("invalid-token", "newpass123")

    @pytest.mark.asyncio
    async def test_reset_password_token_used_twice(self, user_service, test_user):
        """Test that reset token can only be used once."""
        token = await user_service.create_password_reset_token(test_user.email)

        # First use should succeed
        await user_service.reset_password_with_token(token, "newpassword123")

        # Second use should fail
        with pytest.raises(TokenInvalidError):
            await user_service.reset_password_with_token(token, "anotherpass123")

    @pytest.mark.asyncio
    async def test_password_change_invalidates_reset_tokens(
        self, user_service, test_user
    ):
        """Test that changing password invalidates existing reset tokens."""
        token = await user_service.create_password_reset_token(test_user.email)

        # Change password directly
        await user_service.set_password(test_user.id, "changedpassword123")

        # Token should be invalidated
        with pytest.raises(TokenInvalidError):
            await user_service.reset_password_with_token(token, "anotherpass123")


class TestUserServiceTokenCleanup:
    """Tests for token cleanup operations."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens(self, user_service, test_user, user_settings):
        """Test cleaning up expired tokens."""
        # Create tokens
        await user_service.create_verification_token(test_user.id)
        await user_service.create_password_reset_token(test_user.email)

        # Cleanup (tokens aren't expired yet, so count should be 0)
        deleted = await user_service.cleanup_expired_tokens()

        # No tokens should be deleted since they're not expired
        assert deleted == 0
