"""Scaffolding logic to initialize frontend structure."""

import shutil
import subprocess
import sys
from pathlib import Path

try:
    from importlib.resources import files
except ImportError:
    # Python < 3.9 fallback
    from importlib_resources import files  # type: ignore


def scaffold_frontend(
    _templates_dir: str = "frontend/templates",
    _static_dir: str = "frontend/static",
) -> None:
    """
    Copy stub files to user's project and install Node dependencies.

    Args:
        templates_dir: Where to create templates directory
        static_dir: Where to create static directory

    This creates:
    - package.json (Vite, Tailwind 4, DaisyUI 5)
    - vite.config.js
    - frontend/css/input.css
    - frontend/js/*.js
    - frontend/templates/*.html
    - .gitignore
    """
    print("🎨 Initializing myfy frontend...")

    # Get stubs directory from package resources
    # First try importlib.resources (works for installed packages)
    stubs_path = files("myfy.frontend").joinpath("stubs")

    # Convert to Path and check if it exists
    stubs_path_resolved = Path(str(stubs_path))

    # If not found, try relative to this file (for editable installs)
    if not stubs_path_resolved.exists():
        # In editable mode: __file__ is in source, stubs are at package root
        package_root = Path(__file__).parent.parent.parent
        stubs_path_resolved = package_root / "stubs"

    if not stubs_path_resolved.exists():
        print("❌ Error: Stubs directory not found in package")
        print(f"   Looking for: {stubs_path_resolved}")
        sys.exit(1)

    project_root = Path.cwd()

    # Copy configuration files to project root
    config_files = ["package.json", "vite.config.js", ".gitignore", "app.py"]
    for file_name in config_files:
        src = stubs_path_resolved / file_name
        dest = project_root / file_name

        if dest.exists():
            print(f"⏭️  Skipping {file_name} (already exists)")
        elif src.exists():
            shutil.copy2(src, dest)
            print(f"✅ Created {file_name}")
        else:
            print(f"⚠️  Warning: {file_name} not found in stubs")

    # Copy frontend directory structure
    frontend_src = stubs_path_resolved / "frontend"
    frontend_dest = project_root / "frontend"

    if frontend_dest.exists():
        print("⏭️  Skipping frontend/ (already exists)")
    elif frontend_src.exists():
        shutil.copytree(frontend_src, frontend_dest)
        print("✅ Created frontend/ directory structure")
    else:
        print("⚠️  Warning: frontend/ directory not found in stubs")

    # Install Node dependencies
    package_json = project_root / "package.json"
    if package_json.exists():
        print("\n📦 Installing Node dependencies...")
        print("   This may take a minute...")

        try:
            subprocess.run(
                ["npm", "install"],
                cwd=project_root,
                check=True,
                capture_output=True,
                text=True,
            )
            print("✅ Node dependencies installed!")
        except subprocess.CalledProcessError as e:
            print("❌ Failed to install Node dependencies:")
            print(f"   {e.stderr}")
            print("\n   Please run 'npm install' manually")
        except FileNotFoundError:
            print("⚠️  npm not found. Please install Node.js and run 'npm install'")
    else:
        print("⚠️  package.json not found, skipping npm install")

    print("\n✨ Frontend initialized successfully!")
    print("\nNext steps:")
    print("  1. Run 'uv run myfy run' to start your app")
    print("  2. Edit frontend/templates/ to create your pages")
    print("  3. Customize frontend/css/input.css for your styles")


def check_frontend_initialized(templates_dir: str = "frontend/templates") -> bool:
    """
    Check if frontend has been initialized.

    Returns:
        True if frontend directory exists, False otherwise
    """
    return Path(templates_dir).exists()
