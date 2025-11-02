"""
Frontend module for myfy with Tailwind 4, DaisyUI 5, and Vite.

Provides server-side rendering with Jinja2 templates, modern CSS/JS bundling,
and zero-config setup for rapid development.
"""

from .build import BuildError, build_frontend, ensure_npm_dependencies_installed
from .module import FrontendModule
from .templates import render_template
from .version import __version__

__all__ = [
    "BuildError",
    "FrontendModule",
    "__version__",
    "build_frontend",
    "ensure_npm_dependencies_installed",
    "render_template",
]
