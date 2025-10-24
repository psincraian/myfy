"""
ASGI adapter using Starlette.

Integrates myfy routing and DI with ASGI protocol.
"""

from typing import List, Any
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.routing import Route as StarletteRoute, Mount
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from .routing import Route, Router
from .context import RequestContext, set_request_context, clear_request_context
from .handlers import HandlerExecutor


class ASGIApp:
    """
    ASGI application adapter.

    Bridges myfy routes and DI with Starlette's ASGI implementation.
    """

    def __init__(self, container: Any, router: Router, lifespan: Any = None):
        """
        Create ASGI app.

        Args:
            container: DI container (must be compiled)
            router: Router with registered routes
            lifespan: Lifespan context manager (optional)
        """
        self.container = container
        self.router = router
        self.executor = HandlerExecutor(container)

        # Compile all routes
        for route in router.get_routes():
            self.executor.compile_route(route)

        # Build Starlette app
        self.app = self._build_starlette_app(lifespan)

    def _build_starlette_app(self, lifespan: Any = None) -> Starlette:
        """Build the underlying Starlette application."""
        # Convert myfy routes to Starlette routes
        starlette_routes = []
        for route in self.router.get_routes():
            starlette_routes.append(
                StarletteRoute(
                    route.path,
                    endpoint=self._make_endpoint(route),
                    methods=[route.method.value],
                    name=route.name,
                )
            )

        # Get CORS settings from container
        middleware = []
        try:
            from .config import WebSettings
            web_settings = self.container.get(WebSettings)

            # Only enable CORS if explicitly configured
            if web_settings.cors_enabled and web_settings.cors_allowed_origins:
                middleware.append(
                    Middleware(
                        CORSMiddleware,
                        allow_origins=web_settings.cors_allowed_origins,
                        allow_credentials=web_settings.cors_allow_credentials,
                        allow_methods=web_settings.cors_allowed_methods,
                        allow_headers=web_settings.cors_allowed_headers,
                        max_age=600,  # Cache preflight requests for 10 minutes
                    )
                )
        except Exception:
            # If settings not available, don't enable CORS (secure default)
            pass

        # Create Starlette app
        return Starlette(
            routes=starlette_routes,
            lifespan=lifespan,
            middleware=middleware,
        )

    def _make_endpoint(self, route: Route):
        """
        Create a Starlette endpoint function for a myfy route.

        This endpoint:
        1. Sets up request context
        2. Injects request scope into DI
        3. Executes the handler with DI
        4. Cleans up request scope
        """

        async def endpoint(request: Request) -> Response:
            # Create request context
            context = RequestContext(request)
            set_request_context(context)

            # Setup request scope in DI
            from myfy.core.di import ScopeContext

            # Initialize request scope bag explicitly (thread-safe)
            ScopeContext.init_request_scope()

            try:
                # Execute handler with DI
                path_params = request.path_params
                response = await self.executor.execute_route(
                    route, request, path_params
                )
                return response

            finally:
                # Cleanup
                clear_request_context()
                ScopeContext.clear_request_bag()

        return endpoint

    async def __call__(self, scope, receive, send):
        """ASGI interface - delegate to Starlette."""
        await self.app(scope, receive, send)

    def __repr__(self) -> str:
        return f"ASGIApp(routes={len(self.router.get_routes())})"
