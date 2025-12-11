"""Jinja2 template system integration."""

from typing import Any

from markupsafe import Markup
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from .assets import AssetResolver
from .config import FrontendSettings


def create_theme_script(storage_key: str) -> Markup:
    """
    Generate inline script for theme initialization.

    This script runs synchronously before CSS loads to prevent
    flash of wrong theme (FOWT) on page navigation.

    Args:
        storage_key: localStorage key for theme preference

    Returns:
        Safe HTML markup with the script tag
    """
    if not storage_key:
        return Markup("")

    script = f"""<script>(function(){{var t=localStorage.getItem('{storage_key}');if(!t){{t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}}document.documentElement.setAttribute('data-theme',t)}})();</script>"""
    return Markup(script)


def create_templates_instance(
    directory: str,
    settings: FrontendSettings,
    asset_resolver: AssetResolver,
) -> Jinja2Templates:
    """
    Create Jinja2 templates instance with asset helpers.

    Args:
        directory: Path to templates directory
        settings: Frontend settings
        asset_resolver: Asset resolver instance

    Returns:
        Configured Jinja2Templates instance
    """
    templates = Jinja2Templates(
        directory=directory,
        autoescape=settings.auto_escape,
        auto_reload=settings.auto_reload and settings.environment == "development",
    )

    # Inject asset helper functions into all templates
    templates.env.globals["get_asset_url"] = asset_resolver.get_asset_url
    templates.env.globals["get_css_url"] = asset_resolver.get_css_url
    templates.env.globals["get_vite_client_url"] = asset_resolver.get_vite_client_url

    # Theme script helper (prevents flash of wrong theme on page load)
    theme_script = create_theme_script(settings.theme_storage_key)
    templates.env.globals["get_theme_script"] = lambda: theme_script

    # Add environment info
    templates.env.globals["environment"] = settings.environment

    return templates


def render_template(
    template_name: str,
    request: Request | None = None,
    templates: Jinja2Templates | None = None,
    **context: Any,
) -> HTMLResponse:
    """
    Render a template with context.

    Args:
        template_name: Template file name (e.g., "home.html")
        request: Starlette request object (optional but recommended)
        templates: Jinja2Templates instance (injected via DI or from module)
        **context: Template context variables

    Returns:
        HTMLResponse with rendered template

    Example with DI injection:
        @route.get("/")
        async def home(request: Request, templates: Jinja2Templates):
            return render_template("home.html", request=request, templates=templates, title="Welcome")

    Example using module-stored templates (convenience):
        from myfy.frontend import frontend_module

        @route.get("/")
        async def home(request: Request):
            return render_template("home.html", request=request,
                                 templates=frontend_module.templates, title="Welcome")
    """
    if templates is None:
        raise RuntimeError(
            "templates parameter is required. Either:\n"
            "1. Inject Jinja2Templates via DI in your handler\n"
            "2. Pass frontend_module.templates explicitly\n"
            "3. Get templates from DI container"
        )

    # Create dummy request if not provided (for compatibility)
    if request is None:
        from starlette.datastructures import URL, Headers  # noqa: PLC0415
        from starlette.requests import Request as StarletteRequest  # noqa: PLC0415

        request = StarletteRequest(
            {
                "type": "http",
                "method": "GET",
                "url": URL("/"),
                "headers": Headers(),
                "query_string": b"",
            }
        )

    # Add request to context
    context["request"] = request

    return templates.TemplateResponse(template_name, context)
