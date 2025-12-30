"""
Authentication module for myfy.

Provides type-based authentication:
- Anonymous: Base identity, always available
- Authenticated: Requires auth, 401 if provider returns None

Quick Start::

    from dataclasses import dataclass
    from myfy.core import Application
    from myfy.web import WebModule, route
    from myfy.web.auth import AuthModule, Authenticated

    # 1. Define your user type
    @dataclass
    class User(Authenticated):
        email: str

    # 2. Create auth provider
    def my_auth(request: Request, jwt: JWTService) -> User | None:
        token = request.headers.get("Authorization")
        if not token:
            return None  # Returns 401
        return jwt.decode(token)

    # 3. Configure module
    app = Application()
    app.add_module(WebModule())
    app.add_module(AuthModule(authenticated_provider=my_auth))

    # 4. Use in routes - just use types!
    @route.get("/profile")
    async def profile(user: User) -> dict:
        return {"id": user.id, "email": user.email}

Route Patterns:

+----------------------------------+-----------------------------------+
| Handler Signature                | Behavior                          |
+==================================+===================================+
| async def route()                | Public, no auth                   |
+----------------------------------+-----------------------------------+
| async def route(a: Anonymous)    | Public, with identity context     |
+----------------------------------+-----------------------------------+
| async def route(u: Authenticated)| Auth required, 401 if None        |
+----------------------------------+-----------------------------------+
| async def route(u: User)         | Auth required (User extends Auth) |
+----------------------------------+-----------------------------------+
| async def route(a: AdminUser)    | 403 if None (if configured)       |
+----------------------------------+-----------------------------------+
"""

from .module import AuthModule
from .registry import ProtectedTypesRegistry
from .types import Anonymous, Authenticated

__all__ = [
    "Anonymous",
    "AuthModule",
    "Authenticated",
    "ProtectedTypesRegistry",
]
