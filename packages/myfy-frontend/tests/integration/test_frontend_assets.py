"""
Integration tests for myfy-frontend asset resolution.

These tests verify:
- AssetResolver behavior in dev and production modes
- Vite manifest parsing
- URL generation for assets and CSS
"""

import json
import tempfile
from pathlib import Path

import pytest

from myfy.frontend.assets import AssetResolver
from myfy.frontend.config import FrontendSettings

pytestmark = pytest.mark.integration


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def dev_settings() -> FrontendSettings:
    """Frontend settings for development mode."""
    return FrontendSettings(
        environment="development",
        enable_vite_dev=True,
        vite_dev_server="http://localhost:5173",
        static_url_prefix="/static",
    )


@pytest.fixture
def prod_settings() -> FrontendSettings:
    """Frontend settings for production mode."""
    return FrontendSettings(
        environment="production",
        enable_vite_dev=False,
        static_url_prefix="/static",
    )


@pytest.fixture
def temp_static_dir():
    """Create a temporary static directory with a manifest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        static_dir = Path(tmpdir) / "static"
        dist_dir = static_dir / "dist"
        vite_dir = dist_dir / ".vite"
        vite_dir.mkdir(parents=True)

        # Create a sample manifest
        manifest = {
            "frontend/js/main.js": {
                "file": "assets/main-abc123.js",
                "isEntry": True,
                "name": "main",
                "src": "frontend/js/main.js",
            },
            "frontend/js/theme-switcher.js": {
                "file": "assets/theme-switcher-def456.js",
                "isEntry": True,
                "name": "theme-switcher",
                "src": "frontend/js/theme-switcher.js",
            },
            "frontend/css/input.css": {
                "file": "assets/input-ghi789.css",
                "src": "frontend/css/input.css",
            },
        }

        (vite_dir / "manifest.json").write_text(json.dumps(manifest))

        yield str(static_dir)


# =============================================================================
# Development Mode Tests
# =============================================================================


class TestAssetResolverDevelopment:
    """Test asset resolution in development mode."""

    def test_is_development_returns_true(self, dev_settings):
        """Test is_development returns True in dev mode."""
        resolver = AssetResolver(static_dir="frontend/static", settings=dev_settings)
        assert resolver.is_development() is True

    def test_get_asset_url_returns_vite_dev_url(self, dev_settings):
        """Test that asset URLs point to Vite dev server."""
        resolver = AssetResolver(static_dir="frontend/static", settings=dev_settings)

        url = resolver.get_asset_url("main")

        assert url == "http://localhost:5173/frontend/js/main.js"

    def test_get_asset_url_for_theme_switcher(self, dev_settings):
        """Test theme-switcher asset URL in dev mode."""
        resolver = AssetResolver(static_dir="frontend/static", settings=dev_settings)

        url = resolver.get_asset_url("theme-switcher")

        assert url == "http://localhost:5173/frontend/js/theme-switcher.js"

    def test_get_css_url_returns_vite_dev_url(self, dev_settings):
        """Test that CSS URL points to Vite dev server."""
        resolver = AssetResolver(static_dir="frontend/static", settings=dev_settings)

        url = resolver.get_css_url("styles")

        assert url == "http://localhost:5173/frontend/css/input.css"

    def test_get_vite_client_url_returns_client(self, dev_settings):
        """Test that Vite client URL is returned in dev mode."""
        resolver = AssetResolver(static_dir="frontend/static", settings=dev_settings)

        url = resolver.get_vite_client_url()

        assert url == "http://localhost:5173/@vite/client"


# =============================================================================
# Production Mode Tests
# =============================================================================


class TestAssetResolverProduction:
    """Test asset resolution in production mode."""

    def test_is_development_returns_false(self, prod_settings, temp_static_dir):
        """Test is_development returns False in prod mode."""
        resolver = AssetResolver(static_dir=temp_static_dir, settings=prod_settings)
        assert resolver.is_development() is False

    def test_get_asset_url_returns_hashed_url(self, prod_settings, temp_static_dir):
        """Test that asset URLs have hashed filenames in production."""
        resolver = AssetResolver(static_dir=temp_static_dir, settings=prod_settings)

        url = resolver.get_asset_url("main")

        assert url == "/static/assets/main-abc123.js"

    def test_get_asset_url_for_theme_switcher_production(self, prod_settings, temp_static_dir):
        """Test theme-switcher asset URL in production."""
        resolver = AssetResolver(static_dir=temp_static_dir, settings=prod_settings)

        url = resolver.get_asset_url("theme-switcher")

        assert url == "/static/assets/theme-switcher-def456.js"

    def test_get_css_url_returns_hashed_url(self, prod_settings, temp_static_dir):
        """Test that CSS URL has hashed filename in production."""
        resolver = AssetResolver(static_dir=temp_static_dir, settings=prod_settings)

        url = resolver.get_css_url("styles")

        assert url == "/static/assets/input-ghi789.css"

    def test_get_vite_client_url_returns_none_in_production(self, prod_settings, temp_static_dir):
        """Test that Vite client URL is None in production."""
        resolver = AssetResolver(static_dir=temp_static_dir, settings=prod_settings)

        url = resolver.get_vite_client_url()

        assert url is None

    def test_get_asset_url_returns_none_for_unknown_entry(self, prod_settings, temp_static_dir):
        """Test that unknown entries return None."""
        resolver = AssetResolver(static_dir=temp_static_dir, settings=prod_settings)

        url = resolver.get_asset_url("nonexistent")

        assert url is None


# =============================================================================
# Manifest Loading Tests
# =============================================================================


class TestManifestLoading:
    """Test manifest loading and caching."""

    def test_load_manifest_returns_dict(self, prod_settings, temp_static_dir):
        """Test that load_manifest returns parsed JSON."""
        resolver = AssetResolver(static_dir=temp_static_dir, settings=prod_settings)

        manifest = resolver.load_manifest()

        assert isinstance(manifest, dict)
        assert "frontend/js/main.js" in manifest

    def test_load_manifest_returns_empty_when_missing(self, prod_settings):
        """Test that load_manifest returns empty dict when file missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = AssetResolver(static_dir=tmpdir, settings=prod_settings)

            manifest = resolver.load_manifest()

            assert manifest == {}

    def test_manifest_is_cached(self, prod_settings, temp_static_dir):
        """Test that manifest is cached after first load."""
        resolver = AssetResolver(static_dir=temp_static_dir, settings=prod_settings)

        # First load
        manifest1 = resolver.load_manifest()
        # Second load (should be cached)
        manifest2 = resolver.load_manifest()

        assert manifest1 is manifest2  # Same object = cached

    def test_clear_cache_reloads_manifest(self, prod_settings, temp_static_dir):
        """Test that clear_cache allows reloading manifest."""
        resolver = AssetResolver(static_dir=temp_static_dir, settings=prod_settings)

        # First load
        manifest1 = resolver.load_manifest()

        # Clear cache
        resolver.clear_cache()

        # Second load (should reload)
        manifest2 = resolver.load_manifest()

        # Contents should be equal but objects might differ
        assert manifest1 == manifest2


# =============================================================================
# Edge Cases
# =============================================================================


class TestAssetResolverEdgeCases:
    """Test edge cases in asset resolution."""

    def test_custom_static_url_prefix(self, temp_static_dir):
        """Test that custom static URL prefix is used."""
        settings = FrontendSettings(
            environment="production",
            enable_vite_dev=False,
            static_url_prefix="/assets",
        )
        resolver = AssetResolver(static_dir=temp_static_dir, settings=settings)

        url = resolver.get_asset_url("main")

        assert url is not None
        assert url.startswith("/assets/")

    def test_dev_mode_with_vite_disabled(self, temp_static_dir):
        """Test development mode with Vite dev server disabled."""
        settings = FrontendSettings(
            environment="development",
            enable_vite_dev=False,  # Disabled
            static_url_prefix="/static",
        )
        resolver = AssetResolver(static_dir=temp_static_dir, settings=settings)

        # Should fall back to production-style URLs (from manifest)
        url = resolver.get_asset_url("main")

        # With vite disabled, it should use manifest even in dev
        assert url == "/static/assets/main-abc123.js"

    def test_custom_vite_dev_server_url(self):
        """Test custom Vite dev server URL."""
        settings = FrontendSettings(
            environment="development",
            enable_vite_dev=True,
            vite_dev_server="http://127.0.0.1:3000",
        )
        resolver = AssetResolver(static_dir="frontend/static", settings=settings)

        url = resolver.get_asset_url("main")

        assert url == "http://127.0.0.1:3000/frontend/js/main.js"

    def test_get_css_url_ignores_entry_name_in_production(self, prod_settings, temp_static_dir):
        """Test that CSS URL in production mode returns input.css regardless of entry name."""
        resolver = AssetResolver(static_dir=temp_static_dir, settings=prod_settings)

        # In production, get_css_url always looks for frontend/css/input.css in manifest
        # regardless of the entry_name parameter
        url = resolver.get_css_url("unknown")

        # Returns the CSS URL since input.css is in the manifest
        assert url == "/static/assets/input-ghi789.css"
