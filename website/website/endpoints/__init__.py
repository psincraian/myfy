"""HTTP endpoint handlers package.

This package contains all route handlers organized by feature.
Routes are automatically registered when the modules are imported.
"""

# Import all endpoints to register routes
from . import health, landing, newsletter, static

__all__ = ["health", "landing", "newsletter", "static"]
