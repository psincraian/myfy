"""
Frontend module for myfy with Tailwind 4, DaisyUI 5, and Vite.

Provides server-side rendering with Jinja2 templates, modern CSS/JS bundling,
and zero-config setup for rapid development.
"""

from .module import FrontendModule
from .templates import render_template
from .version import __version__

__all__ = ["FrontendModule", "__version__", "render_template"]
