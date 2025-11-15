"""Landing page endpoints."""

from datetime import UTC, datetime

from starlette.requests import Request
from starlette.templating import Jinja2Templates

from myfy.frontend import render_template
from myfy.web import route


@route.get("/")
async def landing(request: Request, templates: Jinja2Templates):
    """Landing page with hero, features, and quickstart.

    Args:
        request: HTTP request
        templates: Jinja2 templates (DI-injected)

    Returns:
        Rendered landing page template
    """
    return render_template(
        "landing.html",
        request=request,
        templates=templates,
        current_year=datetime.now(tz=UTC).year,
    )
