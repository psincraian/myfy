"""
Application kernel - lifecycle and module management.

Usage:
    from myfy.core.kernel import Application, Module, BaseModule

    app = Application()
    app.add_module(MyModule())
    await app.run()
"""

from .app import Application
from .module import Module, BaseModule
from .lifecycle import LifecycleManager

__all__ = [
    "Application",
    "Module",
    "BaseModule",
    "LifecycleManager",
]
