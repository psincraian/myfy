"""
Integration tests for web+frontend application.

Tests WebModule + FrontendModule integration:
- Template rendering with Jinja2
- Template inheritance
- Context injection
- Static file serving
- Module dependency (FrontendModule requires WebModule)
"""

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


# =============================================================================
# Template Rendering Tests
# =============================================================================


class TestTemplateRendering:
    """Test Jinja2 template rendering."""

    def test_index_page_renders(self, test_client: TestClient):
        """Index page renders with template."""
        response = test_client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Check content from base template
        html = response.text
        assert "<!DOCTYPE html>" in html
        assert "<html" in html

    def test_index_page_has_app_name(self, test_client: TestClient):
        """Index page includes app name from settings."""
        response = test_client.get("/")

        html = response.text
        assert "Web Frontend Test App" in html

    def test_index_page_has_title(self, test_client: TestClient):
        """Index page includes title in head."""
        response = test_client.get("/")

        html = response.text
        assert "<title>" in html
        assert "Home" in html


# =============================================================================
# Template Context Tests
# =============================================================================


class TestTemplateContext:
    """Test template context injection."""

    def test_user_page_with_name(self, test_client: TestClient):
        """User page receives name from path parameter."""
        response = test_client.get("/user/Alice")

        assert response.status_code == 200
        html = response.text
        assert "Hello, Alice!" in html

    def test_user_page_with_different_names(self, test_client: TestClient):
        """Different users get different content."""
        alice_response = test_client.get("/user/Alice")
        bob_response = test_client.get("/user/Bob")

        assert "Alice" in alice_response.text
        assert "Bob" in bob_response.text
        assert "Alice" not in bob_response.text


# =============================================================================
# Template Inheritance Tests
# =============================================================================


class TestTemplateInheritance:
    """Test Jinja2 template inheritance."""

    def test_extends_base_template(self, test_client: TestClient):
        """Child templates extend base template."""
        response = test_client.get("/")

        html = response.text
        # Check base template elements
        assert "<header>" in html
        assert "<footer>" in html
        assert "<main>" in html

    def test_block_override(self, test_client: TestClient):
        """Child templates can override blocks."""
        response = test_client.get("/")

        html = response.text
        # Content block should have welcome message
        assert "Welcome to" in html


# =============================================================================
# Template Loop Tests
# =============================================================================


class TestTemplateLoops:
    """Test Jinja2 loop constructs."""

    def test_list_page_renders_items(self, test_client: TestClient):
        """List page renders all items."""
        response = test_client.get("/list")

        assert response.status_code == 200
        html = response.text

        # Check all items are rendered
        assert "Item 1" in html
        assert "Item 2" in html
        assert "Item 3" in html

    def test_list_page_has_values(self, test_client: TestClient):
        """List page shows item values."""
        response = test_client.get("/list")

        html = response.text
        assert "100" in html
        assert "200" in html
        assert "300" in html

    def test_list_page_has_count(self, test_client: TestClient):
        """List page shows item count from filter."""
        response = test_client.get("/list")

        html = response.text
        assert "Total items: 3" in html


# =============================================================================
# Error Template Tests
# =============================================================================


class TestErrorTemplates:
    """Test error page templates."""

    def test_error_page_renders(self, test_client: TestClient):
        """Error page renders with error code."""
        response = test_client.get("/error/404")

        assert response.status_code == 200
        html = response.text
        assert "Error 404" in html

    def test_error_page_message(self, test_client: TestClient):
        """Error page shows error message."""
        response = test_client.get("/error/500")

        html = response.text
        assert "An error occurred with code 500" in html


# =============================================================================
# Static File Tests
# =============================================================================


class TestStaticFiles:
    """Test static file serving."""

    def test_static_css_served(self, test_client: TestClient):
        """CSS static file is served correctly."""
        response = test_client.get("/static/style.css")

        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]
        assert "font-family" in response.text

    def test_static_js_served(self, test_client: TestClient):
        """JS static file is served correctly."""
        response = test_client.get("/static/app.js")

        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]
        assert "console.log" in response.text

    def test_nonexistent_static_returns_404(self, test_client: TestClient):
        """Non-existent static file returns 404."""
        response = test_client.get("/static/nonexistent.css")

        assert response.status_code == 404


# =============================================================================
# Module Integration Tests
# =============================================================================


class TestModuleIntegration:
    """Test FrontendModule integration with WebModule."""

    def test_health_endpoint_works(self, test_client: TestClient):
        """JSON endpoints still work alongside templates."""
        response = test_client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_templates_injected_via_di(self, test_client: TestClient):
        """Jinja2Templates is properly injected via DI."""
        # If templates weren't injected, the page wouldn't render
        response = test_client.get("/")
        assert response.status_code == 200
        assert "<!DOCTYPE html>" in response.text


# =============================================================================
# Module Dependency Tests
# =============================================================================


class TestModuleDependency:
    """Test FrontendModule's dependency on WebModule."""

    def test_frontend_requires_web(self, tmp_path):
        """FrontendModule declares WebModule as dependency."""
        from myfy.frontend import FrontendModule
        from myfy.web import WebModule

        module = FrontendModule(
            templates_dir=str(tmp_path / "templates"),
            static_dir=str(tmp_path / "static"),
        )

        assert WebModule in module.requires

    def test_frontend_without_web_fails(self, tmp_path):
        """Application with FrontendModule but no WebModule fails."""
        from myfy.core import Application
        from myfy.core.kernel import ModuleDependencyError
        from myfy.frontend import FrontendModule

        (tmp_path / "templates").mkdir()
        (tmp_path / "templates" / "base.html").write_text("<html></html>")

        app = Application(auto_discover=False)
        app.add_module(
            FrontendModule(
                templates_dir=str(tmp_path / "templates"),
                static_dir=str(tmp_path / "static"),
            )
        )

        with pytest.raises(ModuleDependencyError, match="WebModule"):
            app.initialize()


# =============================================================================
# Lifecycle Tests
# =============================================================================


class TestFrontendLifecycle:
    """Test FrontendModule lifecycle."""

    @pytest.mark.asyncio
    async def test_lifespan_works(self, web_frontend_app):
        """Application lifespan works with frontend module."""
        app, _, _ = web_frontend_app

        lifespan = app.create_lifespan()
        async with lifespan(None):
            # Should complete without errors
            pass
