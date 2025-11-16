"""Custom StaticFiles middleware with cache control headers."""

from starlette.staticfiles import StaticFiles
from starlette.types import Receive, Scope, Send


class CachedStaticFiles(StaticFiles):
    """
    StaticFiles subclass that adds Cache-Control headers to responses.

    This ensures that static assets (CSS, JS, images) are properly cached
    by browsers and CDNs, improving performance and reducing server load.

    Args:
        directory: Directory path for static files
        cache_max_age: Maximum age in seconds for cache (default: 31536000 = 1 year)
        enable_caching: Whether to add cache headers (default: True)
        **kwargs: Additional arguments passed to StaticFiles
    """

    def __init__(
        self,
        *,
        directory: str,
        cache_max_age: int = 31536000,
        enable_caching: bool = True,
        **kwargs,
    ):
        super().__init__(directory=directory, **kwargs)
        self.cache_max_age = cache_max_age
        self.enable_caching = enable_caching

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI callable that wraps StaticFiles to inject cache headers.

        Intercepts the response to add Cache-Control headers before sending
        to the client.
        """
        if scope["type"] != "http":
            await super().__call__(scope, receive, send)
            return

        async def send_wrapper(message):
            """Wrapper to inject cache headers into response."""
            if message["type"] == "http.response.start" and self.enable_caching:
                headers = list(message.get("headers", []))

                # Add Cache-Control header
                # Using "public" to allow caching by browsers and CDNs
                # Using "immutable" for assets (which are typically hashed in production)
                cache_control = f"public, max-age={self.cache_max_age}, immutable"
                headers.append((b"cache-control", cache_control.encode()))

                message = {**message, "headers": headers}

            await send(message)

        await super().__call__(scope, receive, send_wrapper)
