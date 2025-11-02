"""Build logic for frontend assets."""

import subprocess
from pathlib import Path


class BuildError(Exception):
    """Raised when build fails."""


def ensure_npm_dependencies_installed(timeout: int = 300) -> None:
    """
    Ensure npm dependencies are installed.

    Args:
        timeout: Timeout in seconds for npm install

    Raises:
        BuildError: If npm install fails or times out
    """
    node_modules = Path("node_modules")
    if node_modules.exists():
        return

    try:
        subprocess.run(
            ["npm", "install"],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise BuildError(
            f"npm install timed out after {timeout} seconds. "
            "Please check your network connection and try again."
        ) from e
    except subprocess.CalledProcessError as e:
        raise BuildError(f"Failed to install dependencies: {e.stderr}") from e
    except FileNotFoundError as e:
        raise BuildError("npm not found. Please install Node.js to build the frontend.") from e


def build_frontend(timeout: int = 300) -> str:
    """
    Build frontend assets for production.

    Runs npm run build to execute Vite build, which:
    - Compiles JavaScript and CSS with Vite
    - Generates unique hashes for each asset (e.g., main-abc123.js)
    - Creates manifest.json mapping source files to hashed versions
    - Outputs to frontend/static/dist/

    Args:
        timeout: Timeout in seconds for the build process

    Returns:
        Build output as string

    Raises:
        BuildError: If package.json is missing, build fails, or times out
    """
    # Check if package.json exists
    package_json = Path("package.json")
    if not package_json.exists():
        raise BuildError(
            "No package.json found. "
            "Please run 'myfy frontend init' first to initialize the frontend."
        )

    # Ensure dependencies are installed
    ensure_npm_dependencies_installed(timeout=timeout)

    # Run the build
    try:
        result = subprocess.run(
            ["npm", "run", "build"],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout
    except subprocess.TimeoutExpired as e:
        raise BuildError(
            f"Build timed out after {timeout} seconds. "
            "The build process is taking too long. Please check for issues."
        ) from e
    except subprocess.CalledProcessError as e:
        error_msg = "Build failed"
        if e.stderr:
            error_msg += f": {e.stderr}"
        if e.stdout:
            error_msg += f"\n{e.stdout}"
        raise BuildError(error_msg) from e
    except FileNotFoundError as e:
        raise BuildError("npm not found. Please install Node.js to build the frontend.") from e
