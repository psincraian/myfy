"""myfy landing page application."""

import logging
import os
import sys
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Add current directory to Python path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from database import DatabaseModule
from dotenv import load_dotenv
from email_validator import EmailNotValidError, validate_email
from newsletter_service import NewsletterService
from security_module import SecurityModule
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.templating import Jinja2Templates

from myfy.core import Application
from myfy.frontend import FrontendModule, render_template
from myfy.web import WebModule, route

# Load environment variables
load_dotenv()


# Get secret key from environment
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set")


# Configure logging
def setup_logging():
    """Configure application logging."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create formatters
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # File handler (rotates at 10MB, keeps 5 backups)
    file_handler = RotatingFileHandler(
        log_dir / "myfy.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


# Set up logging
setup_logging()
logger = logging.getLogger(__name__)


# Get database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://myfy:myfy_dev@localhost:5432/myfy_db"
)

# Create application
app = Application(auto_discover=False)

# Add modules
app.add_module(WebModule())
app.add_module(FrontendModule())  # Frontend module handles templates and static files
app.add_module(DatabaseModule(database_url=DATABASE_URL))

# Add security module (handles CSRF, rate limiting, security headers)
security_module = SecurityModule(secret_key=SECRET_KEY)
app.add_module(security_module)


# Routes
@route.get("/")
async def landing(request: Request, templates: Jinja2Templates):
    """Landing page with hero, features, and quickstart."""
    return render_template(
        "landing.html",
        request=request,
        templates=templates,
        current_year=datetime.now(tz=UTC).year,
    )


@route.get("/newsletter")
async def newsletter_page(request: Request, templates: Jinja2Templates):
    """Newsletter signup page."""
    return render_template(
        "newsletter.html",
        request=request,
        templates=templates,
        current_year=datetime.now(tz=UTC).year,
        success=False,
        error=False,
    )


@route.post("/newsletter")
@security_module.limiter.limit("5/minute")
async def newsletter_subscribe(
    request: Request, templates: Jinja2Templates, session_maker: async_sessionmaker
):
    """Handle newsletter subscription form submission."""
    logger.info(f"Newsletter subscription attempt from {request.client.host}")

    # Parse form data
    form_data = await request.form()
    email = form_data.get("email", "").strip()
    csrf_token = form_data.get("csrf_token", "").strip()

    # Validate CSRF token
    if not csrf_token or not security_module.validate_csrf_token(csrf_token):
        logger.warning(
            f"CSRF validation failed for newsletter subscription from {request.client.host}"
        )
        return render_template(
            "newsletter.html",
            request=request,
            templates=templates,
            current_year=datetime.now(tz=UTC).year,
            success=False,
            error=True,
            message="Security validation failed. Please try again.",
        )

    # Validate email is provided
    if not email:
        return render_template(
            "newsletter.html",
            request=request,
            templates=templates,
            current_year=datetime.now(tz=UTC).year,
            success=False,
            error=True,
            message="Please provide an email address.",
        )

    # Validate email length
    if len(email) > 255:
        return render_template(
            "newsletter.html",
            request=request,
            templates=templates,
            current_year=datetime.now(tz=UTC).year,
            success=False,
            error=True,
            message="Email address is too long.",
        )

    # Validate email format using email-validator library
    try:
        valid = validate_email(email, check_deliverability=False)
        email = valid.normalized  # Use normalized form
    except EmailNotValidError:
        logger.warning(f"Invalid email format attempt: {email}")
        return render_template(
            "newsletter.html",
            request=request,
            templates=templates,
            current_year=datetime.now(tz=UTC).year,
            success=False,
            error=True,
            message="Please provide a valid email address.",
        )

    # Save to database
    async with session_maker() as session:
        service = NewsletterService(session)
        success, message = await service.subscribe(email)

    if success:
        logger.info(f"Newsletter subscription successful for {email}")
    else:
        logger.warning(f"Newsletter subscription failed for {email}: {message}")

    return render_template(
        "newsletter.html",
        request=request,
        templates=templates,
        current_year=datetime.now(tz=UTC).year,
        success=success,
        error=not success,
        message=message,
    )


@route.get("/health")
async def health_check(session_maker: async_sessionmaker):
    """Health check endpoint for monitoring and load balancers."""
    try:
        # Check database connectivity
        async with session_maker() as session:
            await session.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(app.run())
