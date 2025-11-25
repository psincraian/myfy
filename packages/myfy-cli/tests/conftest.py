"""
Shared pytest fixtures for myfy-cli tests.

This module provides:
- CLI runner fixtures
- Temporary application directory fixtures
"""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


# =============================================================================
# CLI Fixtures
# =============================================================================


@pytest.fixture
def cli_runner():
    """Provide a Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_app_dir():
    """Create a temporary directory with a test application."""
    with tempfile.TemporaryDirectory() as tmpdir:
        app_file = Path(tmpdir) / "app.py"
        app_file.write_text(
            """
from myfy.core import Application
from myfy.core.config import BaseSettings
from myfy.web import WebModule, route

class AppSettings(BaseSettings):
    app_name: str = "Test App"

@route.get("/health")
async def health():
    return {"status": "ok"}

app = Application(settings_class=AppSettings, auto_discover=False)
app.add_module(WebModule())
"""
        )

        # Change to temp directory for tests
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        yield tmpdir
        os.chdir(original_dir)


@pytest.fixture
def temp_app_dir_no_app():
    """Create a temporary directory without an application."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        yield tmpdir
        os.chdir(original_dir)
