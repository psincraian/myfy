"""Integration tests for authentication routes."""

from __future__ import annotations

import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.testclient import TestClient

from myfy.core.di import REQUEST, SINGLETON, Container
from myfy.user.auth.password import PasswordHasher
from myfy.user.auth.session import SessionManager
from myfy.user.config import UserSettings
from myfy.user.models.base import DefaultUser
from myfy.user.routes import auth
from myfy.user.services.user import UserService
from myfy.web.asgi import ASGIApp
from myfy.web.routing import Router

pytestmark = pytest.mark.integration


# =============================================================================
# Helper Functions (module-level for proper type resolution)
# =============================================================================


def _create_user_service_factory(user_model):
    """Create a UserService factory function with proper type annotations."""

    def factory(
        session: AsyncSession,
        hasher: PasswordHasher,
        settings: UserSettings,
    ) -> UserService:
        return UserService(
            session=session,
            user_model=user_model,
            password_hasher=hasher,
            settings=settings,
        )

    return factory


def _create_test_app(
    router: Router,
    settings: UserSettings,
    password_hasher: PasswordHasher,
    session_manager: SessionManager,
    async_engine,
) -> tuple[ASGIApp, Container]:
    """Create a test application with the given configuration."""
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    container = Container()
    container.register(type_=Router, factory=lambda: router, scope=SINGLETON)
    container.register(type_=UserSettings, factory=lambda: settings, scope=SINGLETON)
    container.register(type_=PasswordHasher, factory=lambda: password_hasher, scope=SINGLETON)
    container.register(type_=SessionManager, factory=lambda: session_manager, scope=SINGLETON)
    container.register(
        type_=AsyncSession,
        factory=lambda: session_factory(),
        scope=REQUEST,
    )
    container.register(
        type_=UserService,
        factory=_create_user_service_factory(DefaultUser),
        scope=REQUEST,
    )
    container.compile()

    auth.register_routes(router, settings)
    app = ASGIApp(container, router)

    return app, container


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def router():
    """Create a fresh router for each test."""
    return Router()


@pytest.fixture
def test_settings():
    """Create test user settings."""
    return UserSettings(
        secret_key=SecretStr("test-secret-key-for-testing-only-32chars!"),
        password_min_length=8,
        password_algorithm="argon2",
        session_lifetime=3600,
        session_secure=False,
        session_httponly=True,
        session_samesite="lax",
        jwt_algorithm="HS256",
        require_email_verification=False,
        allow_registration=True,
        allow_password_login=True,
        after_login_url="/dashboard",
        after_logout_url="/",
        after_register_url="/login",
        login_url="/login",
        register_url="/register",
    )


@pytest.fixture
def password_hasher(test_settings):
    """Create password hasher."""
    return PasswordHasher.from_settings(test_settings)


@pytest.fixture
def session_manager(test_settings):
    """Create session manager."""
    return SessionManager.from_settings(test_settings)


@pytest.fixture
def setup_app(
    router,
    test_settings,
    password_hasher,
    session_manager,
    async_engine,
):
    """Set up application with auth routes."""
    return _create_test_app(
        router=router,
        settings=test_settings,
        password_hasher=password_hasher,
        session_manager=session_manager,
        async_engine=async_engine,
    )


@pytest.fixture
def client(setup_app):
    """Create test client."""
    app, _ = setup_app
    return TestClient(app.app, follow_redirects=False)


@pytest.fixture
def container(setup_app):
    """Get container from setup."""
    _, container = setup_app
    return container


# =============================================================================
# Login Page Tests
# =============================================================================


class TestLoginPage:
    """Tests for GET /login endpoint."""

    def test_login_page_returns_config(self, client):
        """Test login page returns configuration data."""
        response = client.get("/login")

        assert response.status_code == 200
        data = response.json()
        assert "allow_registration" in data
        assert "allow_password_login" in data
        assert "oauth_providers" in data

    def test_login_page_includes_registration_flag(self, client, test_settings):
        """Test login page includes registration availability."""
        response = client.get("/login")
        data = response.json()

        assert data["allow_registration"] == test_settings.allow_registration


# =============================================================================
# Login Submit Tests
# =============================================================================


class TestLoginSubmit:
    """Tests for POST /login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, client, async_session, password_hasher, test_settings):
        """Test successful login."""
        # First create a user directly using the session
        user_service = UserService(
            session=async_session,
            user_model=DefaultUser,
            password_hasher=password_hasher,
            settings=test_settings,
        )
        await user_service.create(
            email="login@example.com",
            password="password123",
            email_verified=True,
        )

        # Attempt login
        response = client.post(
            "/login",
            json={"email": "login@example.com", "password": "password123"},
        )

        # Should redirect to after_login_url
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"

        # Should have session cookie
        assert "myfy_session" in response.cookies

    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self, client, async_session, password_hasher, test_settings
    ):
        """Test login with invalid password."""
        user_service = UserService(
            session=async_session,
            user_model=DefaultUser,
            password_hasher=password_hasher,
            settings=test_settings,
        )
        await user_service.create(
            email="wrongpass@example.com",
            password="password123",
            email_verified=True,
        )

        response = client.post(
            "/login",
            json={"email": "wrongpass@example.com", "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert "error" in response.json()

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post(
            "/login",
            json={"email": "nonexistent@example.com", "password": "password123"},
        )

        assert response.status_code == 401
        assert "error" in response.json()

    @pytest.mark.asyncio
    async def test_login_unverified_email_when_required(
        self, async_engine, async_session, password_hasher
    ):
        """Test login with unverified email when verification is required."""
        router = Router()

        # Create settings that require email verification
        settings = UserSettings(
            secret_key=SecretStr("test-secret-key-for-testing-only-32chars!"),
            require_email_verification=True,
            session_secure=False,
        )
        session_manager = SessionManager.from_settings(settings)

        app, _ = _create_test_app(
            router=router,
            settings=settings,
            password_hasher=password_hasher,
            session_manager=session_manager,
            async_engine=async_engine,
        )
        test_client = TestClient(app.app, follow_redirects=False)

        # Create unverified user
        user_service = UserService(
            session=async_session,
            user_model=DefaultUser,
            password_hasher=password_hasher,
            settings=settings,
        )
        await user_service.create(
            email="unverified@example.com",
            password="password123",
            email_verified=False,  # Not verified
        )

        response = test_client.post(
            "/login",
            json={"email": "unverified@example.com", "password": "password123"},
        )

        assert response.status_code == 403
        assert "verify" in response.json()["error"].lower()


# =============================================================================
# Logout Tests
# =============================================================================


class TestLogout:
    """Tests for POST /logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_clears_session(
        self, client, async_session, password_hasher, test_settings
    ):
        """Test logout clears session cookie."""
        # First create a user
        user_service = UserService(
            session=async_session,
            user_model=DefaultUser,
            password_hasher=password_hasher,
            settings=test_settings,
        )
        await user_service.create(
            email="logout@example.com",
            password="password123",
            email_verified=True,
        )

        # Login first
        login_response = client.post(
            "/login",
            json={"email": "logout@example.com", "password": "password123"},
        )
        assert login_response.status_code == 303

        # Then logout
        response = client.post("/logout")

        assert response.status_code == 303
        assert response.headers["location"] == "/"

    def test_logout_without_session(self, client):
        """Test logout works even without session."""
        response = client.post("/logout")

        assert response.status_code == 303
        assert response.headers["location"] == "/"


# =============================================================================
# Registration Page Tests
# =============================================================================


class TestRegistrationPage:
    """Tests for GET /register endpoint."""

    def test_register_page_returns_config(self, client):
        """Test registration page returns config."""
        response = client.get("/register")

        assert response.status_code == 200
        data = response.json()
        assert "allow_registration" in data
        assert "oauth_providers" in data

    @pytest.mark.asyncio
    async def test_register_page_redirects_when_disabled(self, async_engine, password_hasher):
        """Test registration page redirects when registration is disabled."""
        router = Router()

        settings = UserSettings(
            secret_key=SecretStr("test-secret-key-for-testing-only-32chars!"),
            allow_registration=False,  # Disabled
            session_secure=False,
        )
        session_manager = SessionManager.from_settings(settings)

        app, _ = _create_test_app(
            router=router,
            settings=settings,
            password_hasher=password_hasher,
            session_manager=session_manager,
            async_engine=async_engine,
        )
        client = TestClient(app.app, follow_redirects=False)

        response = client.get("/register")

        assert response.status_code == 303
        assert response.headers["location"] == "/login"


# =============================================================================
# Registration Submit Tests
# =============================================================================


class TestRegistrationSubmit:
    """Tests for POST /register endpoint."""

    def test_register_success(self, client):
        """Test successful registration."""
        response = client.post(
            "/register",
            json={
                "email": "newuser@example.com",
                "password": "securepass123",
                "password_confirm": "securepass123",
            },
        )

        # Should redirect to after_register_url
        assert response.status_code == 303
        assert response.headers["location"] == "/login"

    def test_register_passwords_mismatch(self, client):
        """Test registration with mismatched passwords."""
        response = client.post(
            "/register",
            json={
                "email": "mismatch@example.com",
                "password": "password123",
                "password_confirm": "differentpassword",
            },
        )

        assert response.status_code == 400
        assert "match" in response.json()["error"].lower()

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, client, async_session, password_hasher, test_settings
    ):
        """Test registration with existing email."""
        # Create existing user
        user_service = UserService(
            session=async_session,
            user_model=DefaultUser,
            password_hasher=password_hasher,
            settings=test_settings,
        )
        await user_service.create(
            email="existing@example.com",
            password="password123",
        )

        response = client.post(
            "/register",
            json={
                "email": "existing@example.com",
                "password": "password123",
                "password_confirm": "password123",
            },
        )

        assert response.status_code == 400
        assert "exists" in response.json()["error"].lower()

    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        response = client.post(
            "/register",
            json={
                "email": "weak@example.com",
                "password": "short",  # Too short
                "password_confirm": "short",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_disabled(self, async_engine, password_hasher):
        """Test registration when disabled."""
        router = Router()

        settings = UserSettings(
            secret_key=SecretStr("test-secret-key-for-testing-only-32chars!"),
            allow_registration=False,  # Disabled
            session_secure=False,
        )
        session_manager = SessionManager.from_settings(settings)

        app, _ = _create_test_app(
            router=router,
            settings=settings,
            password_hasher=password_hasher,
            session_manager=session_manager,
            async_engine=async_engine,
        )
        client = TestClient(app.app, follow_redirects=False)

        response = client.post(
            "/register",
            json={
                "email": "newuser@example.com",
                "password": "password123",
                "password_confirm": "password123",
            },
        )

        assert response.status_code == 403
        assert "disabled" in response.json()["error"].lower()

    def test_register_with_display_name(self, client):
        """Test registration with display name."""
        response = client.post(
            "/register",
            json={
                "email": "displayname@example.com",
                "password": "securepass123",
                "password_confirm": "securepass123",
                "display_name": "John Doe",
            },
        )

        assert response.status_code == 303

    @pytest.mark.asyncio
    async def test_register_requires_verification(self, async_engine, password_hasher):
        """Test registration when email verification is required."""
        router = Router()

        settings = UserSettings(
            secret_key=SecretStr("test-secret-key-for-testing-only-32chars!"),
            require_email_verification=True,
            session_secure=False,
        )
        session_manager = SessionManager.from_settings(settings)

        app, _ = _create_test_app(
            router=router,
            settings=settings,
            password_hasher=password_hasher,
            session_manager=session_manager,
            async_engine=async_engine,
        )
        client = TestClient(app.app, follow_redirects=False)

        response = client.post(
            "/register",
            json={
                "email": "verify@example.com",
                "password": "securepass123",
                "password_confirm": "securepass123",
            },
        )

        # Should return JSON message about verification
        assert response.status_code == 200
        data = response.json()
        assert "verify" in data["message"].lower() or "email" in data["message"].lower()
        assert "user_id" in data
