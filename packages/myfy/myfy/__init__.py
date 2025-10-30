"""
myfy: Opinionated Python framework with modularity, ergonomics, and power.

This is a meta-package that bundles the core myfy components for convenience.

Install options:
    pip install myfy          # Core + CLI
    pip install myfy[web]     # Core + CLI + Web
    pip install myfy[all]     # Everything
"""

# Namespace package for myfy
# See PEP 420 - Implicit Namespace Packages
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .version import __version__

__all__ = ["__version__"]
