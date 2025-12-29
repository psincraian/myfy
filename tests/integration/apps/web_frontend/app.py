"""
Web + Frontend example application.

A complete application using WebModule + FrontendModule to verify:
- Template rendering with Jinja2
- Static file serving
- Template context injection
- Asset resolution
"""

from pathlib import Path

from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from myfy.core import Application
from myfy.core.config import BaseSettings
from myfy.frontend import FrontendModule
from myfy.frontend.config import FrontendSettings
from myfy.web import WebModule
from myfy.web.routing import Router


# =============================================================================
# Settings
# =============================================================================


class WebFrontendSettings(BaseSettings):
    """Settings for web+frontend test application."""

    app_name: str = "Web Frontend Test App"
    debug: bool = True
    page_title: str = "Test Page"

    model_config = {"env_prefix": "WEB_FRONTEND_TEST_"}


# =============================================================================
# Template Setup
# =============================================================================


def setup_test_templates(templates_dir: Path, static_dir: Path):
    """
    Create test templates and static files.

    This creates a minimal set of templates for testing.
    """
    templates_dir.mkdir(parents=True, exist_ok=True)
    static_dir.mkdir(parents=True, exist_ok=True)

    # Create base template
    (templates_dir / "base.html").write_text(
        """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}{{ title }}{% endblock %}</title>
</head>
<body>
    <header>
        <h1>{{ app_name }}</h1>
    </header>
    <main>
        {% block content %}{% endblock %}
    </main>
    <footer>
        <p>&copy; 2024 Test App</p>
    </footer>
</body>
</html>"""
    )

    # Create index template
    (templates_dir / "index.html").write_text(
        """{% extends "base.html" %}

{% block title %}Home - {{ app_name }}{% endblock %}

{% block content %}
<h2>Welcome to {{ app_name }}</h2>
<p>This is the home page.</p>
{% if user %}
<p>Hello, {{ user.name }}!</p>
{% endif %}
{% endblock %}"""
    )

    # Create error template
    (templates_dir / "error.html").write_text(
        """{% extends "base.html" %}

{% block title %}Error{% endblock %}

{% block content %}
<h2>Error {{ error_code }}</h2>
<p>{{ error_message }}</p>
{% endblock %}"""
    )

    # Create a template with loops
    (templates_dir / "list.html").write_text(
        """{% extends "base.html" %}

{% block title %}{{ title }}{% endblock %}

{% block content %}
<h2>{{ title }}</h2>
<ul>
{% for item in items %}
    <li>{{ item.name }}: {{ item.value }}</li>
{% endfor %}
</ul>
<p>Total items: {{ items | length }}</p>
{% endblock %}"""
    )

    # Create static dist directory (for production-like setup)
    dist_dir = static_dir / "dist"
    dist_dir.mkdir(exist_ok=True)

    # Create a simple CSS file
    (dist_dir / "style.css").write_text(
        """body {
    font-family: sans-serif;
    margin: 0;
    padding: 20px;
}"""
    )

    # Create a simple JS file
    (dist_dir / "app.js").write_text(
        """console.log("App loaded");"""
    )


# =============================================================================
# Application Factory
# =============================================================================


def create_app(base_path: Path) -> tuple[Application, Router, Path, Path]:
    """
    Create the web+frontend test application.

    Args:
        base_path: Base path for templates and static files

    Returns:
        Tuple of (Application, Router, templates_dir, static_dir)
    """
    templates_dir = base_path / "templates"
    static_dir = base_path / "static"

    # Setup templates
    setup_test_templates(templates_dir, static_dir)

    router = Router()

    # =============================================================================
    # Routes
    # =============================================================================

    @router.get("/")
    async def index(
        request: Request,
        templates: Jinja2Templates,
        settings: WebFrontendSettings,
    ) -> HTMLResponse:
        """Home page with template rendering."""
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "app_name": settings.app_name,
                "title": settings.page_title,
            },
        )

    @router.get("/user/{name}")
    async def user_page(
        request: Request,
        name: str,
        templates: Jinja2Templates,
        settings: WebFrontendSettings,
    ) -> HTMLResponse:
        """Page with user context."""
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "app_name": settings.app_name,
                "title": f"Welcome {name}",
                "user": {"name": name},
            },
        )

    @router.get("/list")
    async def list_page(
        request: Request,
        templates: Jinja2Templates,
        settings: WebFrontendSettings,
    ) -> HTMLResponse:
        """Page with list iteration."""
        items = [
            {"name": "Item 1", "value": 100},
            {"name": "Item 2", "value": 200},
            {"name": "Item 3", "value": 300},
        ]
        return templates.TemplateResponse(
            request=request,
            name="list.html",
            context={
                "app_name": settings.app_name,
                "title": "Item List",
                "items": items,
            },
        )

    @router.get("/error/{code}")
    async def error_page(
        request: Request,
        code: int,
        templates: Jinja2Templates,
        settings: WebFrontendSettings,
    ) -> HTMLResponse:
        """Error page template."""
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "app_name": settings.app_name,
                "title": f"Error {code}",
                "error_code": code,
                "error_message": f"An error occurred with code {code}",
            },
        )

    @router.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok"}

    # =============================================================================
    # Create Application
    # =============================================================================

    # Create frontend settings for production-like setup (no Vite dev server)
    frontend_settings = FrontendSettings(
        environment="test",
        templates_dir=str(templates_dir),
        static_dir=str(static_dir),
        enable_vite_dev=False,  # Don't try to start Vite in tests
    )

    app = Application(settings_class=WebFrontendSettings, auto_discover=False)
    app.add_module(WebModule(router=router))
    app.add_module(
        FrontendModule(
            templates_dir=str(templates_dir),
            static_dir=str(static_dir),
            auto_init=False,  # We already created templates
        )
    )

    return app, router, templates_dir, static_dir
