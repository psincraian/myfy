"""
Frontend Demo - myfy with Tailwind 4 + DaisyUI 5

This example demonstrates the FrontendModule with:
- Server-side rendering using Jinja2
- DaisyUI 5 components
- Tailwind 4 styling
- Vite for asset bundling
- Theme switcher (light/dark mode)
"""

from starlette.requests import Request
from starlette.templating import Jinja2Templates

from myfy.core import Application
from myfy.frontend import FrontendModule, render_template
from myfy.web import WebModule, route


# Create routes with DI injection of templates
@route.get("/")
async def home(request: Request, templates: Jinja2Templates):
    """Home page with DaisyUI components."""
    return render_template(
        "home.html",
        request=request,
        templates=templates,
        title="Frontend Demo",
        description="Built with myfy, Tailwind 4, and DaisyUI 5",
    )


@route.get("/about")
async def about(request: Request, templates: Jinja2Templates):
    """About page."""
    return render_template(
        "about.html",
        request=request,
        templates=templates,
        title="About",
    )


@route.get("/components")
async def components(request: Request, templates: Jinja2Templates):
    """Component showcase page."""
    return render_template(
        "components.html",
        request=request,
        templates=templates,
        title="Components",
    )


# Create application
app = Application(auto_discover=False)
app.add_module(WebModule())
app.add_module(FrontendModule(auto_init=True))  # Auto-scaffolds on first run!

if __name__ == "__main__":
    import asyncio

    asyncio.run(app.run())
