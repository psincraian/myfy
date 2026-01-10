"""
Template scaffolding for user authentication pages.
"""

from __future__ import annotations

import shutil
from pathlib import Path


def scaffold_user_templates(
    output_dir: str | Path,
    overwrite: bool = False,
) -> list[str]:
    """
    Scaffold user authentication templates to project directory.

    Copies bundled templates to the specified directory for customization.

    Args:
        output_dir: Directory to copy templates to (e.g., "frontend/templates/auth")
        overwrite: If True, overwrite existing files

    Returns:
        List of created file paths

    Example:
        ```python
        from myfy.user.templates import scaffold_user_templates

        # Scaffold to project
        files = scaffold_user_templates("frontend/templates/auth")
        print(f"Created {len(files)} template files")
        ```
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Get bundled templates directory
    bundled_dir = Path(__file__).parent / "_bundled"

    created_files = []

    if bundled_dir.exists():
        for template_file in bundled_dir.rglob("*.html"):
            # Get relative path from bundled dir
            rel_path = template_file.relative_to(bundled_dir)
            dest_path = output_path / rel_path

            # Skip if exists and not overwriting
            if dest_path.exists() and not overwrite:
                continue

            # Create parent directories
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(template_file, dest_path)
            created_files.append(str(dest_path))

    return created_files


def check_templates_exist(templates_dir: str | Path) -> bool:
    """
    Check if auth templates exist in the specified directory.

    Args:
        templates_dir: Directory to check

    Returns:
        True if templates exist
    """
    path = Path(templates_dir)
    if not path.exists():
        return False

    # Check for key template files
    required = ["login.html", "register.html"]
    for filename in required:
        # Check in root or auth subdirectory
        if not (path / filename).exists() and not (path / "auth" / filename).exists():
            return False

    return True
