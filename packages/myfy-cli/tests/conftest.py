"""
Shared test fixtures for myfy-cli tests.

Provides reusable fixtures for CLI testing.
"""

import pytest


@pytest.fixture
def mock_application():
    """Provide a mock Application instance."""
    from unittest.mock import Mock

    from myfy.core import Application

    mock_app = Mock(spec=Application)
    mock_app._initialized = False
    mock_app._modules = []

    return mock_app


@pytest.fixture
def app_file(tmp_path):
    """Factory for creating test application files."""

    def _factory(filename: str = "app.py", var_name: str = "app", content: str | None = None):
        """
        Create a test application file.

        Args:
            filename: Name of the file (app.py, main.py, etc.)
            var_name: Variable name for the Application instance
            content: Custom file content (uses default if None)

        Returns:
            Path to created file
        """
        if content is None:
            content = f"""
from myfy.core import Application

{var_name} = Application()
"""

        app_path = tmp_path / filename
        app_path.write_text(content)
        return app_path

    return _factory
