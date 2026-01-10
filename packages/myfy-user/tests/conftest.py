"""Test fixtures for myfy-user."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from pydantic import SecretStr
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from myfy.user.config import UserSettings
from myfy.user.models.base import DefaultUser

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.fixture
def user_settings() -> UserSettings:
    """Create test user settings."""
    return UserSettings(
        secret_key=SecretStr("test-secret-key-for-testing-only-32chars!"),
        password_min_length=8,
        password_algorithm="argon2",
        session_lifetime=3600,
        session_secure=False,  # For testing
        jwt_algorithm="HS256",
        jwt_access_token_lifetime=3600,
        jwt_refresh_token_lifetime=86400,
        require_email_verification=False,
        oauth_google_client_id="test-google-client-id",
        oauth_google_client_secret=SecretStr("test-google-client-secret"),
        oauth_github_client_id="test-github-client-id",
        oauth_github_client_secret=SecretStr("test-github-client-secret"),
    )


@pytest_asyncio.fixture
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create async SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        # Import Base and all models to register them with metadata
        from myfy.data import Base

        # Import models to ensure they are registered with Base.metadata
        from myfy.user.models.base import DefaultUser  # noqa: F401
        from myfy.user.models.oauth import OAuthConnection  # noqa: F401
        from myfy.user.models.token import EmailVerificationToken, PasswordResetToken  # noqa: F401

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(
    async_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for testing."""
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session


@pytest.fixture
def password_hasher(user_settings: UserSettings):
    """Create PasswordHasher instance."""
    from myfy.user.auth.password import PasswordHasher

    return PasswordHasher(
        algorithm=user_settings.password_algorithm,
        min_length=user_settings.password_min_length,
    )


@pytest.fixture
def session_manager(user_settings: UserSettings):
    """Create SessionManager instance."""
    from myfy.user.auth.session import SessionManager

    return SessionManager(
        secret_key=user_settings.secret_key.get_secret_value(),
        cookie_name=user_settings.session_cookie_name,
        lifetime=user_settings.session_lifetime,
        secure=user_settings.session_secure,
        httponly=user_settings.session_httponly,
        samesite=user_settings.session_samesite,
    )


@pytest.fixture
def jwt_service(user_settings: UserSettings):
    """Create JWTService instance."""
    from myfy.user.auth.jwt import JWTService

    return JWTService(
        secret_key=user_settings.secret_key.get_secret_value(),
        algorithm=user_settings.jwt_algorithm,
        access_token_lifetime=user_settings.jwt_access_token_lifetime,
        refresh_token_lifetime=user_settings.jwt_refresh_token_lifetime,
    )


@pytest_asyncio.fixture
async def user_service(
    async_session: AsyncSession,
    password_hasher,
    user_settings: UserSettings,
):
    """Create UserService instance with test database."""
    from myfy.user.services.user import UserService

    return UserService(
        session=async_session,
        user_model=DefaultUser,
        password_hasher=password_hasher,
        settings=user_settings,
    )


@pytest_asyncio.fixture
async def test_user(user_service) -> DefaultUser:
    """Create a test user."""
    return await user_service.create(
        email="test@example.com",
        password="password123",
        email_verified=True,
    )


@pytest_asyncio.fixture
async def unverified_user(user_service) -> DefaultUser:
    """Create an unverified test user."""
    return await user_service.create(
        email="unverified@example.com",
        password="password123",
        email_verified=False,
    )


@pytest_asyncio.fixture
async def admin_user(user_service) -> DefaultUser:
    """Create an admin test user."""
    return await user_service.create(
        email="admin@example.com",
        password="adminpass123",
        email_verified=True,
        is_superuser=True,
    )


@pytest.fixture
def mock_request():
    """Create a mock Starlette request."""
    request = MagicMock()
    request.cookies = {}
    request.headers = {}
    return request


@pytest.fixture
def mock_response():
    """Create a mock Starlette response."""
    response = MagicMock()
    response.set_cookie = MagicMock()
    response.delete_cookie = MagicMock()
    return response


@pytest.fixture
def oauth_registry(user_settings: UserSettings):
    """Create OAuth registry with test providers."""
    from myfy.user.oauth.registry import OAuthProviderRegistry

    registry = OAuthProviderRegistry(user_settings)
    registry.register_provider("google")
    registry.register_provider("github")
    return registry


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx AsyncClient for OAuth testing."""
    return AsyncMock()
