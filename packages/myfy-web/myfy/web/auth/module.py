"""
Authentication module for myfy.

Provides type-based authentication with configurable protection.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from myfy.core.di import REQUEST, SINGLETON

from .registry import ProtectedTypesRegistry
from .types import Anonymous, Authenticated

if TYPE_CHECKING:
    from myfy.core.di import Container


class AuthModule:
    """
    Authentication module with type-based protection.

    Behavior:
    - Routes without auth type: Execute normally (public)
    - Routes with Anonymous: Inject Anonymous (always succeeds)
    - Routes with Authenticated: Inject user, 401 if None
    - Routes with custom types: Configurable status codes

    Usage::

        # Basic setup
        app.add_module(AuthModule(
            authenticated_provider=my_auth_provider,
        ))

        # With custom Anonymous and protected types
        app.add_module(AuthModule(
            anonymous_provider=my_anonymous_provider,
            authenticated_provider=my_auth_provider,
            protected_types={
                AdminUser: 403,
            },
        ))

    Override Anonymous::

        @dataclass
        class MyAnonymous(Anonymous):
            ip: str
            session_id: str | None

        def my_anonymous(request: Request) -> MyAnonymous:
            return MyAnonymous(
                ip=request.client.host,
                session_id=request.cookies.get("session"),
            )

    Override Authenticated::

        @dataclass
        class User(Authenticated):
            email: str

        def my_auth(request: Request, jwt: JWTService) -> User | None:
            token = request.headers.get("Authorization")
            if not token:
                return None  # Returns 401
            return jwt.decode(token)
    """

    def __init__(
        self,
        anonymous_provider: Callable[..., Anonymous] | None = None,
        authenticated_provider: Callable[..., Authenticated | None] | None = None,
        protected_types: dict[type, int] | None = None,
    ):
        """
        Create auth module.

        Args:
            anonymous_provider: Override default Anonymous provider.
                               Signature: (request: Request, ...) -> Anonymous
                               Can inject other dependencies via type hints.
            authenticated_provider: Provider for Authenticated type.
                                   Signature: (request: Request, ...) -> Authenticated | None
                                   Return None to trigger 401.
                                   Can inject other dependencies via type hints.
            protected_types: Additional types with custom status codes.
                            Authenticated -> 401 is built-in.
                            Example: {AdminUser: 403}
        """
        self._anonymous_provider = anonymous_provider
        self._authenticated_provider = authenticated_provider
        self._protected_types = {
            Authenticated: 401,
            **(protected_types or {}),
        }

    @property
    def name(self) -> str:
        """Module name."""
        return "auth"

    @property
    def requires(self) -> list[type]:
        """Module dependencies."""
        from myfy.web.module import WebModule  # noqa: PLC0415

        return [WebModule]

    @property
    def provides(self) -> list[type]:
        """Protocols this module implements."""
        return []

    def configure(self, container: "Container") -> None:
        """Register auth providers in DI container."""
        # Anonymous provider - default or user override
        if self._anonymous_provider:
            container.register(
                type_=Anonymous,
                factory=self._anonymous_provider,
                scope=REQUEST,
            )
        else:
            # Default: empty Anonymous
            container.register(
                type_=Anonymous,
                factory=lambda: Anonymous(),
                scope=REQUEST,
            )

        # Authenticated provider - user must provide for auth routes
        if self._authenticated_provider:
            container.register(
                type_=Authenticated,
                factory=self._authenticated_provider,
                scope=REQUEST,
            )

        # Protected types registry - used by HandlerExecutor
        container.register(
            type_=ProtectedTypesRegistry,
            factory=lambda: ProtectedTypesRegistry(self._protected_types),
            scope=SINGLETON,
        )

    def extend(self, container: "Container") -> None:
        """Extend other modules (no-op)."""

    def finalize(self, container: "Container") -> None:
        """Finalize module configuration (no-op)."""

    async def start(self) -> None:
        """Start module (no-op)."""

    async def stop(self) -> None:
        """Stop module (no-op)."""

    def __repr__(self) -> str:
        """String representation."""
        types_str = ", ".join(t.__name__ for t in self._protected_types)
        return f"AuthModule(protected_types=[{types_str}])"
