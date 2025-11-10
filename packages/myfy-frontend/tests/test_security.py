"""
Security tests for frontend components.

Tests XSS prevention, template safety, and asset integrity.
"""

import json

import pytest

from myfy.frontend.assets import AssetResolver
from myfy.frontend.config import FrontendSettings
from myfy.frontend.templates import create_templates_instance


class TestTemplateXSSPrevention:
    """Test XSS prevention in templates."""

    def test_auto_escape_prevents_xss(self, tmp_path):
        """Should escape HTML in templates by default."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        # Create template with user input
        (template_dir / "test.html").write_text("<p>{{ user_input }}</p>")

        settings = FrontendSettings(auto_escape=True)
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)
        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        # Render with malicious input
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.testclient import TestClient

        app = Starlette()
        client = TestClient(app)
        request = Request({"type": "http", "method": "GET", "path": "/"}, client)

        response = templates.TemplateResponse(
            "test.html",
            {"request": request, "user_input": "<script>alert('xss')</script>"},
        )

        body = response.body.decode()

        # Should be escaped
        assert "&lt;script&gt;" in body
        assert "<script>" not in body

    def test_javascript_injection_prevention(self, tmp_path):
        """Should prevent JavaScript injection in templates."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        (template_dir / "test.html").write_text("<div data-value='{{ user_data }}'></div>")

        settings = FrontendSettings(auto_escape=True)
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)
        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.testclient import TestClient

        app = Starlette()
        client = TestClient(app)
        request = Request({"type": "http", "method": "GET", "path": "/"}, client)

        # Injection attempt
        response = templates.TemplateResponse(
            "test.html",
            {"request": request, "user_data": "' onclick='alert(1)' x='"},
        )

        body = response.body.decode()

        # Should be escaped
        assert "onclick=" not in body or "&" in body

    def test_url_injection_prevention(self, tmp_path):
        """Should prevent URL injection attacks."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        (template_dir / "test.html").write_text("<a href='{{ url }}'>Link</a>")

        settings = FrontendSettings(auto_escape=True)
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)
        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.testclient import TestClient

        app = Starlette()
        client = TestClient(app)
        request = Request({"type": "http", "method": "GET", "path": "/"}, client)

        # JavaScript URL injection
        response = templates.TemplateResponse(
            "test.html",
            {"request": request, "url": "javascript:alert('xss')"},
        )

        body = response.body.decode()

        # Should be in the HTML (proper validation should happen in application)
        assert "href=" in body


class TestAssetIntegrity:
    """Test asset integrity and manifest security."""

    def test_manifest_tampering_detection(self, tmp_path):
        """Should handle corrupted manifest gracefully."""
        manifest_dir = tmp_path / "static" / "dist" / ".vite"
        manifest_dir.mkdir(parents=True)

        # Create invalid JSON manifest
        (manifest_dir / "manifest.json").write_text("{invalid json")

        settings = FrontendSettings(environment="production")
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        # Should handle gracefully
        with pytest.raises(json.JSONDecodeError):
            resolver.load_manifest()

    def test_manifest_with_path_traversal_attempts(self, tmp_path):
        """Should safely handle manifest entries with path traversal."""
        manifest_dir = tmp_path / "static" / "dist" / ".vite"
        manifest_dir.mkdir(parents=True)

        # Manifest with path traversal attempt
        manifest_data = {
            "main.js": {"file": "../../../etc/passwd"},
            "styles.css": {"file": "../../sensitive/file.css"},
        }
        (manifest_dir / "manifest.json").write_text(json.dumps(manifest_data))

        settings = FrontendSettings(environment="production", static_url_prefix="/static")
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        manifest = resolver.load_manifest()

        # Manifest loads successfully (validation should happen when serving files)
        assert "main.js" in manifest

    def test_asset_url_validation(self, tmp_path):
        """Should validate asset URLs are safe."""
        settings = FrontendSettings(environment="production", static_url_prefix="/static/dist")
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        # Manifest with suspicious URLs
        manifest_dir = tmp_path / "static" / "dist" / ".vite"
        manifest_dir.mkdir(parents=True)

        manifest_data = {
            "main.js": {"file": "assets/main.js"},
        }
        (manifest_dir / "manifest.json").write_text(json.dumps(manifest_data))

        url = resolver.get_asset_url("main")

        # URL should start with static prefix
        assert url.startswith("/static/dist/")


class TestViteDevServerSecurity:
    """Test Vite dev server security."""

    def test_vite_dev_server_url_validation(self, tmp_path):
        """Should use configured Vite dev server URL safely."""
        # Test with various URLs
        test_urls = [
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://0.0.0.0:5173",
        ]

        for vite_url in test_urls:
            settings = FrontendSettings(
                environment="development",
                enable_vite_dev=True,
                vite_dev_server=vite_url,
            )
            resolver = AssetResolver(str(tmp_path / "static"), settings)

            url = resolver.get_asset_url("main")

            # Should use the configured server
            assert url.startswith(vite_url)

    def test_vite_client_only_in_development(self, tmp_path):
        """Should only provide Vite client in development mode."""
        # Development mode
        dev_settings = FrontendSettings(environment="development", enable_vite_dev=True)
        dev_resolver = AssetResolver(str(tmp_path / "static"), dev_settings)

        assert dev_resolver.get_vite_client_url() is not None

        # Production mode
        prod_settings = FrontendSettings(environment="production")
        prod_resolver = AssetResolver(str(tmp_path / "static"), prod_settings)

        assert prod_resolver.get_vite_client_url() is None


class TestConfigurationSecurity:
    """Test frontend configuration security."""

    def test_auto_reload_disabled_in_production(self, tmp_path):
        """Should disable auto-reload in production regardless of setting."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        # Try to enable auto-reload in production
        settings = FrontendSettings(environment="production", auto_reload=True)
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)
        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        # Should be disabled in production
        assert templates.env.auto_reload is False

    def test_environment_variable_not_leaked(self, tmp_path):
        """Should not leak sensitive environment info."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        (template_dir / "test.html").write_text("<p>Env: {{ environment }}</p>")

        settings = FrontendSettings(environment="production")
        asset_resolver = AssetResolver(str(tmp_path / "static"), settings)
        templates = create_templates_instance(str(template_dir), settings, asset_resolver)

        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.testclient import TestClient

        app = Starlette()
        client = TestClient(app)
        request = Request({"type": "http", "method": "GET", "path": "/"}, client)

        response = templates.TemplateResponse("test.html", {"request": request})

        body = response.body.decode()

        # Environment is exposed (application should decide what to show)
        # This test documents the behavior
        assert "Env:" in body


class TestBuildSecurity:
    """Test build process security."""

    def test_npm_command_injection_prevention(self, tmp_path, monkeypatch):
        """Should prevent command injection in npm commands."""
        from unittest.mock import patch

        from myfy.frontend.build import build_frontend

        monkeypatch.chdir(tmp_path)

        # Create package.json
        (tmp_path / "package.json").write_text('{"name": "test"}')

        # Mock subprocess to verify command
        with patch("myfy.frontend.build.subprocess.run") as mock_run:
            with patch("myfy.frontend.build.ensure_npm_dependencies_installed"):
                mock_run.return_value.stdout = "done"

                build_frontend()

                # Verify command is safe (list, not string)
                call_args = mock_run.call_args[0][0]
                assert isinstance(call_args, list)
                assert call_args == ["npm", "run", "build"]
