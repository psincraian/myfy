"""
DI-specific exceptions with helpful error messages.
"""


class DIError(Exception):
    """Base exception for all DI errors."""


class ProviderNotFoundError(DIError):
    """Raised when a required provider cannot be found."""

    def __init__(self, key: str, resolution_path: list[str] | None = None):
        self.key = key
        self.resolution_path = resolution_path or []
        msg = f"No provider found for: {key}"
        if resolution_path:
            path_str = " → ".join(resolution_path)
            msg += f"\n\nResolution path:\n  {path_str}"
        msg += (
            "\n\nDid you forget to register this dependency with @provider or container.register()?"
        )
        super().__init__(msg)


class CircularDependencyError(DIError):
    """Raised when a circular dependency is detected."""

    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        cycle_str = " → ".join(cycle)
        msg = f"Circular dependency detected:\n  {cycle_str} → {cycle[0]}"
        msg += "\n\nCircular dependencies cannot be resolved. Please refactor to break the cycle."
        super().__init__(msg)


class ScopeMismatchError(DIError):
    """Raised when a dependency scope is invalid (e.g., request-scoped in singleton)."""

    def __init__(self, provider_scope: str, dependency_scope: str, provider_name: str):
        self.provider_scope = provider_scope
        self.dependency_scope = dependency_scope
        self.provider_name = provider_name
        msg = (
            f"Scope mismatch: {provider_name} (scope={provider_scope}) "
            f"cannot depend on a {dependency_scope}-scoped dependency."
        )
        msg += "\n\nSuggestion: singleton cannot inject request/task scoped dependencies."
        super().__init__(msg)


class DuplicateProviderError(DIError):
    """Raised when attempting to register a provider that already exists."""

    def __init__(self, key: str):
        self.key = key
        msg = f"Provider already registered for: {key}"
        msg += "\n\nUse a qualifier to register multiple providers for the same type."
        super().__init__(msg)


class ContainerFrozenError(DIError):
    """Raised when attempting to modify a compiled container."""

    def __init__(self):
        super().__init__(
            "Container is frozen after compilation. "
            "Cannot register new providers after compile() has been called."
        )
