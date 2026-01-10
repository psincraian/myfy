"""
User management module for myfy framework.

Provides complete user authentication and management with:
- Email/password authentication
- OAuth providers (Google, GitHub)
- Session and JWT tokens
- Email verification and password reset
- Subclassable user models
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from myfy.core.config import load_settings
from myfy.core.di import REQUEST, SINGLETON
from myfy.data import DataModule
from myfy.web import WebModule
from myfy.web.auth import AuthModule
from myfy.web.auth.types import Authenticated

from .config import UserSettings
from .extensions import IUserProvider
from .models.base import BaseUser, DefaultUser

if TYPE_CHECKING:
    from sqlalchemy import MetaData

    from myfy.core.di import Container

    from .oauth.registry import OAuthProviderRegistry
    from .services.user import UserService

logger = logging.getLogger(__name__)


class UserModule:
    """
    User management module for myfy.

    Features:
    - Email/password authentication
    - OAuth providers (Google, GitHub, extensible)
    - Subclassable BaseUser model
    - Email verification and password reset
    - Session-based auth (web) and JWT tokens (API)
    - Integration with FrontendModule for templates

    Lifecycle (per ADR-0005):
    - configure(): Register services in DI container
    - extend(): No-op (uses AuthModule's authenticated_provider pattern)
    - finalize(): Register routes on ASGI app
    - start(): Create tables if auto_create_tables=True
    - stop(): No-op

    Example:
        ```python
        from myfy.core import Application
        from myfy.data import DataModule
        from myfy.web import WebModule
        from myfy.web.auth import AuthModule
        from myfy.user import UserModule, BaseUser
        from sqlalchemy import Column, String

        # Extend BaseUser with custom fields
        class User(BaseUser):
            __tablename__ = "users"
            phone: Mapped[str | None] = mapped_column(String(20))

        # Create module
        user_module = UserModule(
            user_model=User,
            oauth_providers=["google", "github"],
        )

        # Set up application
        app = Application()
        app.add_module(DataModule())
        app.add_module(WebModule())
        app.add_module(AuthModule(
            authenticated_provider=user_module.get_authenticated_provider(),
        ))
        app.add_module(user_module)
        ```
    """

    def __init__(
        self,
        settings: UserSettings | None = None,
        user_model: type[BaseUser] | None = None,
        oauth_providers: list[str] | None = None,
        auto_create_tables: bool = False,
        metadata: MetaData | None = None,
        enable_routes: bool = True,
        enable_templates: bool = True,
    ) -> None:
        """
        Create user module.

        Args:
            settings: Custom user settings (defaults to loading from environment)
            user_model: Custom user model class (must extend BaseUser)
            oauth_providers: List of OAuth providers to enable (e.g., ["google", "github"])
            auto_create_tables: If True, auto-create user tables during start()
            metadata: SQLAlchemy MetaData for table registration
            enable_routes: If True, register auth routes (/login, /register, etc.)
            enable_templates: If True, provide Jinja2 templates
        """
        self._settings = settings
        self._user_model = user_model or DefaultUser
        self._oauth_providers = oauth_providers or []
        self._auto_create_tables = auto_create_tables
        self._metadata = metadata
        self._enable_routes = enable_routes
        self._enable_templates = enable_templates

        # Initialized during configure/finalize
        self._oauth_registry: OAuthProviderRegistry | None = None
        self._user_service: UserService | None = None
        self._container: Container | None = None

    @property
    def name(self) -> str:
        """Module name for registration."""
        return "user"

    @property
    def requires(self) -> list[type]:
        """
        Module types this module depends on.

        UserModule requires:
        - DataModule: For database access
        - WebModule: For HTTP routes
        - AuthModule: For authentication integration
        """
        return [DataModule, WebModule, AuthModule]

    @property
    def provides(self) -> list[type]:
        """Extension protocols provided by this module."""
        return [IUserProvider]

    def configure(self, container: Container) -> None:
        """
        Configure user module.

        Registers:
        - UserSettings
        - UserService (factory)
        - PasswordHasher
        - SessionManager
        - JWTService
        - OAuthProviderRegistry
        """
        from sqlalchemy.ext.asyncio import AsyncSession

        from myfy.core.di.types import ProviderKey

        from .auth.jwt import JWTService
        from .auth.password import PasswordHasher
        from .auth.session import SessionManager
        from .oauth.registry import OAuthProviderRegistry
        from .services.user import UserService

        logger.debug("Configuring UserModule...")
        self._container = container

        # Check if UserSettings already registered (from nested app settings)
        key = ProviderKey(UserSettings)
        if key not in container._providers:
            if self._settings is None:
                self._settings = load_settings(UserSettings)
            container.register(
                type_=UserSettings,
                factory=lambda: self._settings,
                scope=SINGLETON,
            )
        else:
            logger.debug("Using nested UserSettings from application")

        # Create password hasher
        def create_password_hasher() -> PasswordHasher:
            settings = container.get(UserSettings)
            return PasswordHasher.from_settings(settings)

        container.register(
            type_=PasswordHasher,
            factory=create_password_hasher,
            scope=SINGLETON,
        )

        # Create session manager
        def create_session_manager() -> SessionManager:
            settings = container.get(UserSettings)
            return SessionManager.from_settings(settings)

        container.register(
            type_=SessionManager,
            factory=create_session_manager,
            scope=SINGLETON,
        )

        # Create JWT service
        def create_jwt_service() -> JWTService:
            settings = container.get(UserSettings)
            return JWTService.from_settings(settings)

        container.register(
            type_=JWTService,
            factory=create_jwt_service,
            scope=SINGLETON,
        )

        # Create OAuth provider registry
        def create_oauth_registry() -> OAuthProviderRegistry:
            settings = container.get(UserSettings)
            registry = OAuthProviderRegistry(settings)
            for provider_name in self._oauth_providers:
                if settings.is_oauth_provider_configured(provider_name):
                    registry.register_provider(provider_name)
                else:
                    logger.warning(
                        f"OAuth provider '{provider_name}' requested but not configured"
                    )
            self._oauth_registry = registry
            return registry

        container.register(
            type_=OAuthProviderRegistry,
            factory=create_oauth_registry,
            scope=SINGLETON,
        )

        # Register user model class for injection
        user_model = self._user_model

        # Create UserService (REQUEST scope - uses request-scoped session)
        def create_user_service(
            session: AsyncSession,
            password_hasher: PasswordHasher,
            settings: UserSettings,
        ) -> UserService:
            return UserService(
                session=session,
                user_model=user_model,
                password_hasher=password_hasher,
                settings=settings,
            )

        container.register(
            type_=UserService,
            factory=create_user_service,
            scope=REQUEST,
        )

        logger.debug("UserModule configured successfully")

    def extend(self, container: Container) -> None:
        """
        Extend other modules' services before container compilation.

        Currently no-op - AuthModule integration is done via authenticated_provider.
        """

    def finalize(self, container: Container) -> None:
        """
        Finalize module configuration after container compilation.

        - Register auth routes on ASGI app
        - Set up template integration
        """
        if self._enable_routes:
            self._register_routes(container)

        if self._enable_templates:
            self._setup_templates(container)

        logger.debug("UserModule finalized")

    async def start(self) -> None:
        """
        Start user module.

        - Create user tables if auto_create_tables=True
        """
        if self._auto_create_tables:
            await self._create_tables()

        logger.info("User module started")

    async def stop(self) -> None:
        """Stop user module (no-op)."""

    def _register_routes(self, container: Container) -> None:
        """Register authentication routes."""
        from myfy.web import Router

        from .routes import auth, oauth, password, profile, verify

        router = container.get(Router)
        settings = container.get(UserSettings)

        # Register auth routes (login, logout, register)
        auth.register_routes(router, settings)

        # Register OAuth routes if providers are configured
        if self._oauth_providers:
            oauth.register_routes(router, settings, self._oauth_providers)

        # Register password routes (forgot, reset)
        password.register_routes(router, settings)

        # Register email verification routes
        verify.register_routes(router, settings)

        # Register profile routes
        profile.register_routes(router, settings)

        logger.debug("Auth routes registered")

    def _setup_templates(self, container: Container) -> None:
        """Set up Jinja2 templates for auth pages."""
        # Templates are bundled with the package and can be overridden
        # by the user's templates directory

    async def _create_tables(self) -> None:
        """Create user-related tables."""
        if self._container is None:
            return

        from sqlalchemy.ext.asyncio import AsyncEngine


        engine = self._container.get(AsyncEngine)

        # Get metadata from user model
        metadata = self._user_model.metadata

        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

        logger.info("User tables created")

    # Public methods for integration

    def get_authenticated_provider(self) -> Callable[..., Awaitable[Authenticated | None]]:
        """
        Get the authenticated_provider for AuthModule integration.

        This provider checks session/JWT tokens and returns User or None.

        Usage:
            ```python
            user_module = UserModule()

            app.add_module(AuthModule(
                authenticated_provider=user_module.get_authenticated_provider(),
            ))
            ```

        Returns:
            Provider function for AuthModule
        """
        from .auth.provider import create_authenticated_provider

        return create_authenticated_provider(self._user_model)

    def get_user_service(self) -> UserService:
        """Get the user service (only available after initialization)."""
        if self._container is None:
            raise RuntimeError("UserModule not initialized")
        from .services.user import UserService

        return self._container.get(UserService)

    def get_oauth_registry(self) -> OAuthProviderRegistry:
        """Get OAuth provider registry (only available after initialization)."""
        if self._oauth_registry is None:
            raise RuntimeError("UserModule not initialized")
        return self._oauth_registry

    def get_user_model(self) -> type[BaseUser]:
        """Get the configured user model class."""
        return self._user_model

    def __repr__(self) -> str:
        """String representation."""
        providers = ", ".join(self._oauth_providers) if self._oauth_providers else "none"
        return f"UserModule(user_model={self._user_model.__name__}, oauth_providers=[{providers}])"


# Module instance for entry point (auto-discovery)
user_module = UserModule()
