"""
Authentication types for myfy.

These are base types that users extend for their own auth needs.
"""

from dataclasses import dataclass


@dataclass
class Anonymous:
    """
    Base identity type - represents any request.

    Always available. Users can override the provider to add
    custom request context (IP, session, geo, etc.).

    Example override::

        @dataclass
        class MyAnonymous(Anonymous):
            ip: str
            session_id: str | None

        def my_anonymous(request: Request) -> MyAnonymous:
            return MyAnonymous(
                ip=request.client.host,
                session_id=request.cookies.get("session"),
            )

        app.add_module(AuthModule(anonymous_provider=my_anonymous))

    Usage in routes::

        @route.get("/info")
        async def info(identity: Anonymous) -> dict:
            return {"status": "ok"}
    """


@dataclass
class Authenticated(Anonymous):
    """
    Authenticated identity - requires valid authentication.

    When a route depends on Authenticated (or subclass) and the
    provider returns None, the framework returns 401 Unauthorized.

    Users should extend this for their own user types::

        @dataclass
        class User(Authenticated):
            email: str
            roles: set[str]

        def my_auth(request: Request, jwt: JWTService) -> User | None:
            token = request.headers.get("Authorization")
            if not token:
                return None  # -> 401
            return jwt.decode(token)

    Usage in routes::

        @route.get("/profile")
        async def profile(user: User) -> dict:
            return {"id": user.id, "email": user.email}
    """

    id: str
