"""
Application kernel - lifecycle and module management.

Usage:
    from myfy.core.kernel import Application, Module, BaseModule

    app = Application()
    app.add_module(MyModule())
    await app.run()
"""

from .app import Application
from .errors import ModuleDependencyError, ModuleError, MyfyModuleNotFoundError
from .lifecycle import LifecycleManager
from .module import BaseModule, Module

__all__ = [
    "Application",
    "BaseModule",
    "LifecycleManager",
    "Module",
    "ModuleDependencyError",
    "ModuleError",
    "MyfyModuleNotFoundError",
]
