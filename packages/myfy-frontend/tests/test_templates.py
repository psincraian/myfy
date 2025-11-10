"""
Tests for Jinja2 template system integration.

Tests template rendering, asset helpers, and environment configuration.
"""

import pytest
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.testclient import TestClient

from myfy.frontend.assets import AssetResolver
from myfy.frontend.config import FrontendSettings
from myfy.frontend.templates import create_templates_instance, render_template


def create_test_request(path: str = "/"):
    """Create a test request."""
    from starlette.applications import Starlette

    app = Starlette()
    client = TestClient(app)
    return Request({"type": "http", "method": "GET", "path": path}, client)


class TestCreateTemplatesInstance:
    """Test templates instance creation."""

    def test_create_templates_instance(self, tmp_path):
        """Should create Jinja2Templates instance."""
        # Create template directory
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        settings = FrontendSettings()
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)

        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        assert templates is not None
        assert hasattr(templates, "env")

    def test_templates_instance_has_asset_helpers(self, tmp_path):
        """Should inject asset helper functions."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        settings = FrontendSettings()
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)

        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        # Check global functions are available
        assert "get_asset_url" in templates.env.globals
        assert "get_css_url" in templates.env.globals
        assert "get_vite_client_url" in templates.env.globals

    def test_templates_instance_has_environment_info(self, tmp_path):
        """Should inject environment information."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        settings = FrontendSettings(environment="production")
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)

        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        assert templates.env.globals["environment"] == "production"

    def test_templates_auto_escape(self, tmp_path):
        """Should configure auto-escaping."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        settings = FrontendSettings(auto_escape=True)
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)

        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        # Auto-escape should be enabled
        assert templates.env.autoescape is True

    def test_templates_auto_reload_in_development(self, tmp_path):
        """Should enable auto-reload in development."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        settings = FrontendSettings(environment="development", auto_reload=True)
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)

        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        assert templates.env.auto_reload is True

    def test_templates_no_auto_reload_in_production(self, tmp_path):
        """Should disable auto-reload in production."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        settings = FrontendSettings(environment="production", auto_reload=True)
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)

        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        # Even if auto_reload is True, should be False in production
        assert templates.env.auto_reload is False


class TestRenderTemplate:
    """Test template rendering."""

    def test_render_simple_template(self, tmp_path):
        """Should render simple template."""
        # Create template
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.html").write_text("<h1>Hello World</h1>")

        settings = FrontendSettings()
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)
        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        request = create_test_request()
        response = render_template("test.html", request=request, templates=templates)

        assert isinstance(response, HTMLResponse)
        assert b"<h1>Hello World</h1>" in response.body

    def test_render_template_with_context(self, tmp_path):
        """Should render template with context variables."""
        # Create template
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.html").write_text("<h1>{{ title }}</h1>")

        settings = FrontendSettings()
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)
        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        request = create_test_request()
        response = render_template("test.html", request=request, templates=templates, title="Test Title")

        assert b"<h1>Test Title</h1>" in response.body

    def test_render_template_without_templates_raises_error(self):
        """Should raise error when templates not provided."""
        request = create_test_request()

        with pytest.raises(RuntimeError, match="templates parameter is required"):
            render_template("test.html", request=request)

    def test_render_template_creates_dummy_request_if_missing(self, tmp_path):
        """Should create dummy request if not provided."""
        # Create template
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.html").write_text("<h1>Test</h1>")

        settings = FrontendSettings()
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)
        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        # Render without request
        response = render_template("test.html", templates=templates)

        assert isinstance(response, HTMLResponse)
        assert b"<h1>Test</h1>" in response.body

    def test_render_template_injects_request_into_context(self, tmp_path):
        """Should inject request into template context."""
        # Create template that uses request
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.html").write_text("<p>Path: {{ request.url.path }}</p>")

        settings = FrontendSettings()
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)
        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        request = create_test_request(path="/test-path")
        response = render_template("test.html", request=request, templates=templates)

        assert b"/test-path" in response.body


class TestAssetHelpersInTemplates:
    """Test asset helpers available in templates."""

    def test_template_can_use_get_asset_url(self, tmp_path):
        """Should use get_asset_url helper in template."""
        # Create template
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.html").write_text(
            '<script src="{{ get_asset_url("main") }}"></script>'
        )

        settings = FrontendSettings(environment="development", enable_vite_dev=True)
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)
        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        request = create_test_request()
        response = render_template("test.html", request=request, templates=templates)

        # Should include vite dev server URL
        assert b"http://localhost:5173" in response.body

    def test_template_can_use_get_css_url(self, tmp_path):
        """Should use get_css_url helper in template."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.html").write_text(
            '<link rel="stylesheet" href="{{ get_css_url("styles") }}">'
        )

        settings = FrontendSettings(environment="development", enable_vite_dev=True)
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)
        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        request = create_test_request()
        response = render_template("test.html", request=request, templates=templates)

        assert b"http://localhost:5173" in response.body
        assert b"input.css" in response.body

    def test_template_can_use_get_vite_client_url(self, tmp_path):
        """Should use get_vite_client_url helper in template."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.html").write_text(
            '{% if get_vite_client_url() %}<script src="{{ get_vite_client_url() }}"></script>{% endif %}'
        )

        settings = FrontendSettings(environment="development", enable_vite_dev=True)
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)
        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        request = create_test_request()
        response = render_template("test.html", request=request, templates=templates)

        assert b"@vite/client" in response.body

    def test_template_environment_variable(self, tmp_path):
        """Should access environment variable in template."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.html").write_text(
            '<p>Environment: {{ environment }}</p>'
        )

        settings = FrontendSettings(environment="production")
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)
        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        request = create_test_request()
        response = render_template("test.html", request=request, templates=templates)

        assert b"Environment: production" in response.body


class TestTemplateErrorHandling:
    """Test template error handling."""

    def test_render_missing_template_raises_error(self, tmp_path):
        """Should raise error for missing template."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        settings = FrontendSettings()
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)
        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        request = create_test_request()

        with pytest.raises(Exception):  # Jinja2 TemplateNotFound
            render_template("nonexistent.html", request=request, templates=templates)

    def test_render_template_with_syntax_error(self, tmp_path):
        """Should raise error for template with syntax error."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "bad.html").write_text("{{ invalid syntax }}")

        settings = FrontendSettings()
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)
        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        request = create_test_request()

        with pytest.raises(Exception):  # Jinja2 TemplateSyntaxError
            render_template("bad.html", request=request, templates=templates)
