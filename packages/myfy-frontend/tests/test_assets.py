"""
Tests for asset management and Vite integration.

Tests asset resolution in development and production modes.
"""

import json

from myfy.frontend.assets import AssetResolver
from myfy.frontend.config import FrontendSettings


class TestAssetResolverDevelopment:
    """Test asset resolver in development mode."""

    def test_is_development_mode(self, tmp_path):
        """Should detect development mode."""
        settings = FrontendSettings(environment="development")
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        assert resolver.is_development() is True

    def test_is_not_development_in_production(self, tmp_path):
        """Should detect production mode."""
        settings = FrontendSettings(environment="production")
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        assert resolver.is_development() is False

    def test_get_asset_url_in_development(self, tmp_path):
        """Should return Vite dev server URL in development."""
        settings = FrontendSettings(
            environment="development",
            enable_vite_dev=True,
            vite_dev_server="http://localhost:5173",
        )
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        url = resolver.get_asset_url("main")

        assert url == "http://localhost:5173/frontend/js/main.js"

    def test_get_asset_url_for_theme_switcher(self, tmp_path):
        """Should return URL for theme-switcher entry."""
        settings = FrontendSettings(
            environment="development",
            enable_vite_dev=True,
        )
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        url = resolver.get_asset_url("theme-switcher")

        assert url == "http://localhost:5173/frontend/js/theme-switcher.js"

    def test_get_asset_url_unknown_entry_returns_none(self, tmp_path):
        """Should return None for unknown entry."""
        settings = FrontendSettings(environment="development", enable_vite_dev=True)
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        url = resolver.get_asset_url("unknown")

        assert url is None

    def test_get_css_url_in_development(self, tmp_path):
        """Should return CSS URL in development."""
        settings = FrontendSettings(environment="development", enable_vite_dev=True)
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        url = resolver.get_css_url("styles")

        assert url == "http://localhost:5173/frontend/css/input.css"

    def test_get_vite_client_url_in_development(self, tmp_path):
        """Should return Vite client URL in development."""
        settings = FrontendSettings(environment="development", enable_vite_dev=True)
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        url = resolver.get_vite_client_url()

        assert url == "http://localhost:5173/@vite/client"

    def test_development_with_vite_dev_disabled(self, tmp_path):
        """Should fall back to production mode when Vite dev disabled."""
        settings = FrontendSettings(environment="development", enable_vite_dev=False)
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        # Should return None since no manifest exists
        url = resolver.get_asset_url("main")

        assert url is None


class TestAssetResolverProduction:
    """Test asset resolver in production mode."""

    def test_load_manifest(self, tmp_path):
        """Should load Vite manifest."""
        # Create manifest
        manifest_dir = tmp_path / "static" / "dist" / ".vite"
        manifest_dir.mkdir(parents=True)

        manifest_data = {
            "frontend/js/main.js": {"file": "assets/main-abc123.js"},
            "frontend/css/input.css": {"file": "assets/input-xyz789.css"},
        }
        (manifest_dir / "manifest.json").write_text(json.dumps(manifest_data))

        settings = FrontendSettings(environment="production")
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        manifest = resolver.load_manifest()

        assert "frontend/js/main.js" in manifest
        assert manifest["frontend/js/main.js"]["file"] == "assets/main-abc123.js"

    def test_load_manifest_missing_returns_empty(self, tmp_path):
        """Should return empty dict if manifest missing."""
        settings = FrontendSettings(environment="production")
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        manifest = resolver.load_manifest()

        assert manifest == {}

    def test_get_asset_url_in_production(self, tmp_path):
        """Should return hashed asset URL in production."""
        # Create manifest
        manifest_dir = tmp_path / "static" / "dist" / ".vite"
        manifest_dir.mkdir(parents=True)

        manifest_data = {
            "frontend/js/main.js": {"file": "assets/main-abc123.js"},
        }
        (manifest_dir / "manifest.json").write_text(json.dumps(manifest_data))

        settings = FrontendSettings(environment="production", static_url_prefix="/static/dist")
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        url = resolver.get_asset_url("main")

        assert url == "/static/dist/assets/main-abc123.js"

    def test_get_css_url_in_production(self, tmp_path):
        """Should return hashed CSS URL in production."""
        manifest_dir = tmp_path / "static" / "dist" / ".vite"
        manifest_dir.mkdir(parents=True)

        manifest_data = {
            "frontend/css/input.css": {"file": "assets/input-xyz789.css"},
        }
        (manifest_dir / "manifest.json").write_text(json.dumps(manifest_data))

        settings = FrontendSettings(environment="production", static_url_prefix="/static/dist")
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        url = resolver.get_css_url("styles")

        assert url == "/static/dist/assets/input-xyz789.css"

    def test_get_vite_client_url_in_production_returns_none(self, tmp_path):
        """Should return None for Vite client in production."""
        settings = FrontendSettings(environment="production")
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        url = resolver.get_vite_client_url()

        assert url is None

    def test_get_asset_url_missing_in_manifest_returns_none(self, tmp_path):
        """Should return None if asset not in manifest."""
        manifest_dir = tmp_path / "static" / "dist" / ".vite"
        manifest_dir.mkdir(parents=True)

        manifest_data = {}
        (manifest_dir / "manifest.json").write_text(json.dumps(manifest_data))

        settings = FrontendSettings(environment="production")
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        url = resolver.get_asset_url("main")

        assert url is None


class TestAssetResolverCaching:
    """Test manifest caching."""

    def test_manifest_caching(self, tmp_path):
        """Should cache manifest after first load."""
        manifest_dir = tmp_path / "static" / "dist" / ".vite"
        manifest_dir.mkdir(parents=True)

        manifest_data = {"frontend/js/main.js": {"file": "assets/main-v1.js"}}
        (manifest_dir / "manifest.json").write_text(json.dumps(manifest_data))

        settings = FrontendSettings(environment="production")
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        # First load
        manifest1 = resolver.load_manifest()
        assert manifest1["frontend/js/main.js"]["file"] == "assets/main-v1.js"

        # Modify manifest file
        manifest_data = {"frontend/js/main.js": {"file": "assets/main-v2.js"}}
        (manifest_dir / "manifest.json").write_text(json.dumps(manifest_data))

        # Second load should still return cached version
        manifest2 = resolver.load_manifest()
        assert manifest2["frontend/js/main.js"]["file"] == "assets/main-v1.js"

    def test_clear_cache(self, tmp_path):
        """Should clear manifest cache."""
        manifest_dir = tmp_path / "static" / "dist" / ".vite"
        manifest_dir.mkdir(parents=True)

        manifest_data = {"frontend/js/main.js": {"file": "assets/main-v1.js"}}
        (manifest_dir / "manifest.json").write_text(json.dumps(manifest_data))

        settings = FrontendSettings(environment="production")
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        # First load
        manifest1 = resolver.load_manifest()
        assert manifest1["frontend/js/main.js"]["file"] == "assets/main-v1.js"

        # Modify manifest and clear cache
        manifest_data = {"frontend/js/main.js": {"file": "assets/main-v2.js"}}
        (manifest_dir / "manifest.json").write_text(json.dumps(manifest_data))
        resolver.clear_cache()

        # Should load new version
        manifest2 = resolver.load_manifest()
        assert manifest2["frontend/js/main.js"]["file"] == "assets/main-v2.js"


class TestAssetResolverConfiguration:
    """Test asset resolver configuration."""

    def test_custom_vite_dev_server(self, tmp_path):
        """Should use custom Vite dev server URL."""
        settings = FrontendSettings(
            environment="development",
            enable_vite_dev=True,
            vite_dev_server="http://custom-host:3000",
        )
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        url = resolver.get_asset_url("main")

        assert url == "http://custom-host:3000/frontend/js/main.js"

    def test_custom_static_url_prefix(self, tmp_path):
        """Should use custom static URL prefix."""
        manifest_dir = tmp_path / "static" / "dist" / ".vite"
        manifest_dir.mkdir(parents=True)

        manifest_data = {
            "frontend/js/main.js": {"file": "assets/main-abc123.js"},
        }
        (manifest_dir / "manifest.json").write_text(json.dumps(manifest_data))

        settings = FrontendSettings(environment="production", static_url_prefix="/custom/static")
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        url = resolver.get_asset_url("main")

        assert url == "/custom/static/assets/main-abc123.js"

    def test_manifest_path_configuration(self, tmp_path):
        """Should use configured manifest path."""
        settings = FrontendSettings(environment="production")
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        expected_path = tmp_path / "static" / "dist" / ".vite" / "manifest.json"
        assert resolver.manifest_path == expected_path


class TestAssetResolverIntegration:
    """Test asset resolver integration scenarios."""

    def test_development_to_production_transition(self, tmp_path):
        """Should handle transition from development to production."""
        # Start in development
        settings_dev = FrontendSettings(environment="development", enable_vite_dev=True)
        resolver_dev = AssetResolver(str(tmp_path / "static"), settings_dev)

        url_dev = resolver_dev.get_asset_url("main")
        assert "localhost:5173" in url_dev

        # Create production manifest
        manifest_dir = tmp_path / "static" / "dist" / ".vite"
        manifest_dir.mkdir(parents=True)

        manifest_data = {
            "frontend/js/main.js": {"file": "assets/main-abc123.js"},
        }
        (manifest_dir / "manifest.json").write_text(json.dumps(manifest_data))

        # Switch to production
        settings_prod = FrontendSettings(environment="production")
        resolver_prod = AssetResolver(str(tmp_path / "static"), settings_prod)

        url_prod = resolver_prod.get_asset_url("main")
        assert "assets/main-abc123.js" in url_prod
        assert "localhost" not in url_prod

    def test_multiple_entries(self, tmp_path):
        """Should resolve multiple entry points."""
        manifest_dir = tmp_path / "static" / "dist" / ".vite"
        manifest_dir.mkdir(parents=True)

        manifest_data = {
            "frontend/js/main.js": {"file": "assets/main-abc123.js"},
            "frontend/js/theme-switcher.js": {"file": "assets/theme-xyz789.js"},
            "frontend/css/input.css": {"file": "assets/input-def456.css"},
        }
        (manifest_dir / "manifest.json").write_text(json.dumps(manifest_data))

        settings = FrontendSettings(environment="production")
        resolver = AssetResolver(str(tmp_path / "static"), settings)

        main_url = resolver.get_asset_url("main")
        theme_url = resolver.get_asset_url("theme-switcher")
        css_url = resolver.get_css_url("styles")

        assert "main-abc123.js" in main_url
        assert "theme-xyz789.js" in theme_url
        assert "input-def456.css" in css_url
