"""Security module for middleware and security headers."""

import logging
import os

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.templating import Jinja2Templates

from myfy.core import Container, Module
from myfy.web import IWebExtension

from ..config import SecuritySettings
from ..services.csrf import CsrfService

logger = logging.getLogger(__name__)


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    def __init__(self, app, environment: str = "production"):
        """Initialize security headers middleware.

        Args:
            app: ASGI application
            environment: Environment mode (development/production)
        """
        super().__init__(app)
        self.environment = environment

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Add CSP - more permissive in development for Vite HMR
        if self.environment == "development":
            # In development, allow Vite dev server (localhost:3001)
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' localhost:3001 http://localhost:3001; "
                "style-src 'self' 'unsafe-inline' localhost:3001 http://localhost:3001; "
                "connect-src 'self' ws://localhost:3001 http://localhost:3001; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:;"
            )
        else:
            # Production CSP - stricter
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:;"
            )
        return response


class SecurityModule(Module, IWebExtension):
    """Module for security features (headers, rate limiting, middleware).

    This module provides comprehensive security features including:
    - Rate limiting with slowapi
    - Security headers (CSP, X-Frame-Options, etc.)
    - Session middleware
    - Trusted host middleware
    - Error handlers

    The module implements IWebExtension to extend the ASGI app with
    middleware and error handlers during application startup.

    Note: CSRF token operations are handled by CsrfService.
    """

    name = "security"

    def __init__(self):
        """Initialize security module."""
        super().__init__()
        self.limiter: Limiter | None = None
        self._settings: SecuritySettings | None = None

    @property
    def provides(self):
        """Declare this module provides IWebExtension."""
        return [IWebExtension]

    def configure(self, container: Container) -> None:
        """Configure the security module.

        Args:
            container: DI container to register services
        """
        # No need to register anything here
        # CsrfService is registered via @provider decorator

    def finalize(self, container: Container) -> None:
        """Finalize the security module after container compilation.

        This is called after the container is compiled, so we can safely
        retrieve settings and initialize security components.

        Args:
            container: DI container (now compiled)
        """
        # Get security settings from container (auto-injected from AppSettings)
        self._settings = container.get(SecuritySettings)

        # Initialize rate limiter
        self.limiter = Limiter(key_func=get_remote_address)

    def extend_asgi_app(self, app: Starlette, container: Container) -> None:
        """Add security middleware to the ASGI app.

        Args:
            app: The Starlette application
            container: DI container
        """
        if not self._settings or not self.limiter:
            raise RuntimeError("Security module not initialized")

        logger.info("Adding security middleware and rate limiting")

        # Detect environment from MYFY_FRONTEND_ENVIRONMENT or default to production
        environment = os.getenv("MYFY_FRONTEND_ENVIRONMENT", "production")

        # Set up rate limiter
        app.state.limiter = self.limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

        # Add session middleware (required for CSRF)
        app.add_middleware(
            SessionMiddleware,
            secret_key=self._settings.secret_key,
            session_cookie="myfy_session",
            max_age=86400,  # 24 hours
            same_site="lax",
            https_only=self._settings.https_only,
        )

        # Add security headers middleware with environment awareness
        app.add_middleware(SecurityHeadersMiddleware, environment=environment)

        # Add trusted host middleware
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=self._settings.allowed_hosts.split(","),
        )

        # Add error handlers
        @app.exception_handler(404)
        async def not_found(request: Request, _exc: HTTPException):
            """Handle 404 errors."""
            logger.warning(f"404 error: {request.url}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Page not found",
                    "status_code": 404,
                },
            )

        @app.exception_handler(500)
        async def server_error(request: Request, exc: Exception):
            """Handle 500 errors."""
            # Log the exception with full traceback
            logger.error(f"Server error on {request.url}: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "status_code": 500,
                },
            )

        # Add CSRF token generator to Jinja2 templates
        try:
            templates = container.get(Jinja2Templates)
            csrf_service = container.get(CsrfService)
            if templates and csrf_service:
                templates.env.globals["csrf_token"] = csrf_service.generate_token
                logger.info("Added CSRF token generator to Jinja2 templates")
        except Exception as e:
            logger.warning(f"Could not add CSRF token to templates: {e}")
