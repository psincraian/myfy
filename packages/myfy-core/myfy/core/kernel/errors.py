"""
Custom exceptions for module and application lifecycle.
"""


class ModuleError(Exception):
    """Base exception for module-related errors."""


class MyfyModuleNotFoundError(ModuleError):
    """Raised when a required module is not found."""

    def __init__(self, module_type: type, message: str | None = None):
        self.module_type = module_type
        if message is None:
            message = f"Module '{module_type.__name__}' not found. Add it via app.add_module()."
        super().__init__(message)


class ModuleDependencyError(ModuleError):
    """Raised when module dependencies cannot be satisfied."""
