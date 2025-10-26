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
from .errors import (
    CircularDependencyError,
    ContainerFrozenError,
    DIError,
    DuplicateProviderError,
    ProviderNotFoundError,
    ScopeMismatchError,
)
from .provider import provider, register_providers_in_container
from .scopes import REQUEST, SINGLETON, TASK, Scope, ScopeContext
from .types import ProviderKey, Qualifier

__all__ = [
    "REQUEST",
    "SINGLETON",
    "TASK",
    "CircularDependencyError",
    "Container",
    "ContainerFrozenError",
    "DIError",
    "DuplicateProviderError",
    "ProviderKey",
    "ProviderNotFoundError",
    "Qualifier",
    "Scope",
    "ScopeContext",
    "ScopeMismatchError",
    "provider",
    "register_providers_in_container",
]
