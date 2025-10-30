"""
Basic myfy app with frontend module.

This example demonstrates:
- Server-side rendering with Jinja2
- DaisyUI 5 components
- Tailwind 4 styling
"""

from starlette.requests import Request
from starlette.templating import Jinja2Templates

from myfy.core import Application
from myfy.frontend import FrontendModule, render_template
from myfy.web import WebModule, route


@route.get("/")
async def home(request: Request, templates: Jinja2Templates):
    """Home page."""
    return render_template(
        "home.html",
        request=request,
        templates=templates,
        title="Welcome to myfy",
    )


# Create application
app = Application(auto_discover=False)
app.add_module(WebModule())
app.add_module(FrontendModule())

if __name__ == "__main__":
    import asyncio

    asyncio.run(app.run())
