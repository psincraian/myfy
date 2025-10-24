"""
Dependency injection system for myfy.

Features:
- Constructor injection with compile-time resolution
- Three scopes: singleton, request, task
- Type-based resolution with optional qualifiers
- Zero reflection on hot path
- Test-friendly overrides

Usage:
    from myfy.core.di import provider, Container, SINGLETON, REQUEST

    @provider(scope=SINGLETON)
    def database(settings: Settings) -> Database:
        return Database(settings.db_url)

    @provider(scope=REQUEST)
    def unit_of_work(db: Database) -> UnitOfWork:
        return UnitOfWork(db)
"""

from .container import Container
from .scopes import Scope, SINGLETON, REQUEST, TASK, ScopeContext
from .types import Qualifier, ProviderKey
from .provider import provider, register_providers_in_container
from .errors import (
    DIError,
    ProviderNotFoundError,
    CircularDependencyError,
    ScopeMismatchError,
    DuplicateProviderError,
    ContainerFrozenError,
)

__all__ = [
    # Core classes
    "Container",
    "ScopeContext",
    # Scopes
    "Scope",
    "SINGLETON",
    "REQUEST",
    "TASK",
    # Decorators
    "provider",
    "register_providers_in_container",
    # Types
    "Qualifier",
    "ProviderKey",
    # Errors
    "DIError",
    "ProviderNotFoundError",
    "CircularDependencyError",
    "ScopeMismatchError",
    "DuplicateProviderError",
    "ContainerFrozenError",
]
