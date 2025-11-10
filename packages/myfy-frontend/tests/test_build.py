"""
Tests for frontend build system.

Tests npm dependency installation and Vite build process.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from myfy.frontend.build import (
    BuildError,
    build_frontend,
    ensure_npm_dependencies_installed,
)


class TestEnsureNpmDependenciesInstalled:
    """Test npm dependency installation."""

    @patch("subprocess.run")
    def test_skip_if_node_modules_exists(self, mock_run, tmp_path, monkeypatch):
        """Should skip installation if node_modules exists."""
        monkeypatch.chdir(tmp_path)

        # Create node_modules directory
        (tmp_path / "node_modules").mkdir()

        ensure_npm_dependencies_installed()

        # Should not call npm install
        mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_install_dependencies_if_missing(self, mock_run, tmp_path, monkeypatch):
        """Should run npm install if node_modules missing."""
        monkeypatch.chdir(tmp_path)

        # Mock successful npm install
        mock_run.return_value = MagicMock(returncode=0)

        ensure_npm_dependencies_installed()

        # Should call npm install
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["npm", "install"]

    @patch("subprocess.run")
    def test_npm_install_timeout(self, mock_run, tmp_path, monkeypatch):
        """Should raise BuildError on timeout."""
        monkeypatch.chdir(tmp_path)

        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired(["npm", "install"], 300)

        with pytest.raises(BuildError, match="timed out"):
            ensure_npm_dependencies_installed(timeout=300)

    @patch("subprocess.run")
    def test_npm_install_failure(self, mock_run, tmp_path, monkeypatch):
        """Should raise BuildError on npm install failure."""
        monkeypatch.chdir(tmp_path)

        # Mock failed npm install
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["npm", "install"], stderr="Error installing packages"
        )

        with pytest.raises(BuildError, match="Failed to install dependencies"):
            ensure_npm_dependencies_installed()

    @patch("subprocess.run")
    def test_npm_not_found(self, mock_run, tmp_path, monkeypatch):
        """Should raise BuildError if npm not found."""
        monkeypatch.chdir(tmp_path)

        # Mock npm not found
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(BuildError, match="npm not found"):
            ensure_npm_dependencies_installed()

    @patch("subprocess.run")
    def test_custom_timeout(self, mock_run, tmp_path, monkeypatch):
        """Should use custom timeout value."""
        monkeypatch.chdir(tmp_path)

        mock_run.return_value = MagicMock(returncode=0)

        ensure_npm_dependencies_installed(timeout=600)

        # Check timeout was passed
        assert mock_run.call_args[1]["timeout"] == 600


class TestBuildFrontend:
    """Test frontend build process."""

    @patch("myfy.frontend.build.ensure_npm_dependencies_installed")
    @patch("subprocess.run")
    def test_build_success(self, mock_run, mock_ensure_deps, tmp_path, monkeypatch):
        """Should build frontend successfully."""
        monkeypatch.chdir(tmp_path)

        # Create package.json
        (tmp_path / "package.json").write_text('{"name": "test"}')

        # Mock successful build
        mock_run.return_value = MagicMock(returncode=0, stdout="Build complete")

        output = build_frontend()

        assert output == "Build complete"
        mock_ensure_deps.assert_called_once()
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["npm", "run", "build"]

    @patch("myfy.frontend.build.ensure_npm_dependencies_installed")
    @patch("subprocess.run")
    def test_build_missing_package_json(self, mock_run, mock_ensure_deps, tmp_path, monkeypatch):
        """Should raise BuildError if package.json missing."""
        monkeypatch.chdir(tmp_path)

        # No package.json

        with pytest.raises(BuildError, match="No package.json found"):
            build_frontend()

        # Should not try to install deps or build
        mock_ensure_deps.assert_not_called()
        mock_run.assert_not_called()

    @patch("myfy.frontend.build.ensure_npm_dependencies_installed")
    @patch("subprocess.run")
    def test_build_timeout(self, mock_run, mock_ensure_deps, tmp_path, monkeypatch):
        """Should raise BuildError on build timeout."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "package.json").write_text('{"name": "test"}')

        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired(["npm", "run", "build"], 300)

        with pytest.raises(BuildError, match="Build timed out"):
            build_frontend(timeout=300)

    @patch("myfy.frontend.build.ensure_npm_dependencies_installed")
    @patch("subprocess.run")
    def test_build_failure(self, mock_run, mock_ensure_deps, tmp_path, monkeypatch):
        """Should raise BuildError on build failure."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "package.json").write_text('{"name": "test"}')

        # Mock failed build
        mock_run.side_effect = subprocess.CalledProcessError(
            1,
            ["npm", "run", "build"],
            stderr="Vite build error",
            stdout="Additional info",
        )

        with pytest.raises(BuildError, match="Build failed"):
            build_frontend()

    @patch("myfy.frontend.build.ensure_npm_dependencies_installed")
    @patch("subprocess.run")
    def test_build_npm_not_found(self, mock_run, mock_ensure_deps, tmp_path, monkeypatch):
        """Should raise BuildError if npm not found."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "package.json").write_text('{"name": "test"}')

        # Mock npm not found
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(BuildError, match="npm not found"):
            build_frontend()

    @patch("myfy.frontend.build.ensure_npm_dependencies_installed")
    @patch("subprocess.run")
    def test_build_custom_timeout(self, mock_run, mock_ensure_deps, tmp_path, monkeypatch):
        """Should use custom timeout."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "package.json").write_text('{"name": "test"}')
        mock_run.return_value = MagicMock(returncode=0, stdout="Done")

        build_frontend(timeout=600)

        # Check timeout was passed
        assert mock_run.call_args[1]["timeout"] == 600

    @patch("myfy.frontend.build.ensure_npm_dependencies_installed")
    @patch("subprocess.run")
    def test_build_captures_output(self, mock_run, mock_ensure_deps, tmp_path, monkeypatch):
        """Should capture and return build output."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "package.json").write_text('{"name": "test"}')
        mock_run.return_value = MagicMock(
            returncode=0, stdout="✓ 15 modules transformed.\nBuild complete!"
        )

        output = build_frontend()

        assert "modules transformed" in output
        assert "Build complete" in output

    @patch("myfy.frontend.build.ensure_npm_dependencies_installed")
    @patch("subprocess.run")
    def test_build_runs_after_dependency_install(
        self, mock_run, mock_ensure_deps, tmp_path, monkeypatch
    ):
        """Should install dependencies before building."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "package.json").write_text('{"name": "test"}')
        mock_run.return_value = MagicMock(returncode=0, stdout="Done")

        build_frontend()

        # Ensure dependencies installed first
        mock_ensure_deps.assert_called_once()
        # Then build
        mock_run.assert_called_once()


class TestBuildErrorHandling:
    """Test error handling and messages."""

    def test_build_error_message_includes_stderr(self, tmp_path, monkeypatch):
        """Should include stderr in error message."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "package.json").write_text('{"name": "test"}')

        with patch("myfy.frontend.build.ensure_npm_dependencies_installed"):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(
                    1,
                    ["npm", "run", "build"],
                    stderr="Error: Module not found",
                )

                with pytest.raises(BuildError) as exc_info:
                    build_frontend()

                assert "Module not found" in str(exc_info.value)

    def test_build_error_message_includes_stdout(self, tmp_path, monkeypatch):
        """Should include stdout in error message."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "package.json").write_text('{"name": "test"}')

        with patch("myfy.frontend.build.ensure_npm_dependencies_installed"):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(
                    1,
                    ["npm", "run", "build"],
                    stderr="",
                    stdout="Warning: Some helpful info",
                )

                with pytest.raises(BuildError) as exc_info:
                    build_frontend()

                assert "helpful info" in str(exc_info.value)

    def test_timeout_error_message(self, tmp_path, monkeypatch):
        """Should have helpful timeout error message."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "package.json").write_text('{"name": "test"}')

        with patch("myfy.frontend.build.ensure_npm_dependencies_installed"):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired(["npm", "run", "build"], 300)

                with pytest.raises(BuildError) as exc_info:
                    build_frontend(timeout=300)

                assert "timed out after 300 seconds" in str(exc_info.value)

    def test_missing_package_json_helpful_message(self, tmp_path, monkeypatch):
        """Should suggest running frontend init."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(BuildError) as exc_info:
            build_frontend()

        assert "myfy frontend init" in str(exc_info.value)


class TestBuildIntegration:
    """Test integration scenarios."""

    @patch("myfy.frontend.build.ensure_npm_dependencies_installed")
    @patch("subprocess.run")
    def test_full_build_workflow(self, mock_run, mock_ensure_deps, tmp_path, monkeypatch):
        """Should execute full build workflow."""
        monkeypatch.chdir(tmp_path)

        # Setup
        (tmp_path / "package.json").write_text('{"name": "test-app"}')
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="vite v4.0.0 building for production...\n✓ 42 modules transformed.\nbuild complete!",
        )

        # Execute build
        output = build_frontend(timeout=300)

        # Verify workflow
        # 1. Dependencies ensured
        mock_ensure_deps.assert_called_once_with(timeout=300)

        # 2. Build executed with correct params
        mock_run.assert_called_once_with(
            ["npm", "run", "build"],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )

        # 3. Output returned
        assert "modules transformed" in output
        assert "build complete" in output
