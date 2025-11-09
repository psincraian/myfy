"""myfy landing page application."""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add current directory to Python path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from database import DatabaseModule
from myfy.core import Application
from myfy.frontend import FrontendModule, render_template
from myfy.web import WebModule, route
from newsletter_service import NewsletterService

# Load environment variables
load_dotenv()

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


# Routes
@route.get("/")
async def landing(request: Request, templates: Jinja2Templates):
    """Landing page with hero, features, and quickstart."""
    return render_template(
        "landing.html",
        request=request,
        templates=templates,
        current_year=datetime.now().year,
    )


@route.get("/newsletter")
async def newsletter_page(request: Request, templates: Jinja2Templates):
    """Newsletter signup page."""
    return render_template(
        "newsletter.html",
        request=request,
        templates=templates,
        current_year=datetime.now().year,
        success=False,
        error=False,
    )


@route.post("/newsletter")
async def newsletter_subscribe(
    request: Request, templates: Jinja2Templates, session_maker: async_sessionmaker
):
    """Handle newsletter subscription form submission."""
    # Parse form data
    form_data = await request.form()
    email = form_data.get("email", "").strip()

    if not email:
        return render_template(
            "newsletter.html",
            request=request,
            templates=templates,
            current_year=datetime.now().year,
            success=False,
            error=True,
            message="Please provide a valid email address.",
        )

    # Save to database
    async with session_maker() as session:
        service = NewsletterService(session)
        success, message = await service.subscribe(email)

    return render_template(
        "newsletter.html",
        request=request,
        templates=templates,
        current_year=datetime.now().year,
        success=success,
        error=not success,
        message=message,
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(app.run())
