"""
Shared test fixtures for myfy-frontend tests.

Provides reusable fixtures for frontend testing.
"""

import json
from pathlib import Path

import pytest

from myfy.frontend.assets import AssetResolver
from myfy.frontend.config import FrontendSettings


@pytest.fixture
def frontend_settings():
    """Provide default frontend settings."""
    return FrontendSettings()


@pytest.fixture
def dev_settings():
    """Provide development mode settings."""
    return FrontendSettings(environment="development", enable_vite_dev=True)


@pytest.fixture
def prod_settings():
    """Provide production mode settings."""
    return FrontendSettings(environment="production")


@pytest.fixture
def static_dir(tmp_path):
    """Provide a temporary static directory."""
    static = tmp_path / "static"
    static.mkdir()
    return static


@pytest.fixture
def template_dir(tmp_path):
    """Provide a temporary templates directory."""
    templates = tmp_path / "templates"
    templates.mkdir()
    return templates


@pytest.fixture
def asset_resolver(static_dir, frontend_settings):
    """Provide an asset resolver instance."""
    return AssetResolver(str(static_dir), frontend_settings)


@pytest.fixture
def manifest_factory(static_dir):
    """Factory for creating Vite manifest files."""

    def _factory(manifest_data: dict):
        """
        Create a Vite manifest.json file.

        Args:
            manifest_data: Dict containing manifest entries

        Returns:
            Path to created manifest file
        """
        manifest_dir = static_dir / "dist" / ".vite"
        manifest_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = manifest_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_data))

        return manifest_path

    return _factory
