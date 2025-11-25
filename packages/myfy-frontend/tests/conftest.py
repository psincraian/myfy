"""
Shared pytest fixtures for myfy-frontend tests.

This module provides:
- Frontend settings fixtures
- Temporary static directory fixtures
"""

import json
import tempfile
from pathlib import Path

import pytest

from myfy.frontend.config import FrontendSettings

# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


# =============================================================================
# Settings Fixtures
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


# =============================================================================
# Static Directory Fixtures
# =============================================================================


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
