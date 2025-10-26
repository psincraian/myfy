"""
Core dependency injection container.

Implements constructor injection with compile-time resolution.
No heavy reflection on the hot path - all type analysis happens at startup.
"""

import threading
from collections.abc import Callable
from contextlib import contextmanager
from inspect import Parameter, signature
from typing import Any, TypeVar, get_type_hints

from .errors import (
    CircularDependencyError,
    ContainerFrozenError,
    DIError,
    DuplicateProviderError,
    ProviderNotFoundError,
    ScopeMismatchError,
)
from .scopes import SINGLETON, Scope, ScopeContext
from .types import ProviderFactory, ProviderKey, Qualifier

T = TypeVar("T")


class ProviderRegistration:
    """Internal representation of a registered provider."""

    def __init__(
        self,
        key: ProviderKey,
        factory: ProviderFactory,
        scope: Scope,
        reloadable_fields: tuple[str, ...] = (),
    ):
        self.key = key
        self.factory = factory
        self.scope = scope
        self.reloadable_fields = reloadable_fields
        self.dependencies: list[ProviderKey] = []
        self.injection_plan: Callable[[], Any] | None = None


class Container:
    """
    Dependency injection container with compile-time resolution.

    Features:
    - Type-based resolution with optional qualifiers
    - Three scopes: singleton, request, task
    - Cycle detection at compile time
    - Zero reflection on hot path (all plans compiled at startup)
    - Test-friendly overrides
    """

    def __init__(self):
        self._providers: dict[ProviderKey, ProviderRegistration] = {}
        self._singletons: dict[ProviderKey, Any] = {}
        self._singleton_locks: dict[ProviderKey, threading.Lock] = {}
        self._frozen = False
        self._override_stack: list[dict[type, ProviderFactory]] = []
        self._has_active_overrides = False

    def register(
        self,
        type_: type[T],
        factory: ProviderFactory[T],
        *,
        scope: Scope = SINGLETON,
        qualifier: str | None = None,
        name: str | None = None,
        reloadable: tuple[str, ...] = (),
    ) -> None:
        """
        Register a provider in the container.

        Args:
            type_: The type this provider produces
            factory: Callable that creates instances
            scope: Lifecycle scope (singleton, request, task)
            qualifier: Optional qualifier for multiple providers of same type
            name: Optional name for resolution
            reloadable: Tuple of field names that can be hot-reloaded

        Raises:
            ContainerFrozenError: If container has been compiled
            DuplicateProviderError: If provider already registered
        """
        if self._frozen:
            raise ContainerFrozenError

        key = ProviderKey(type_, qualifier, name)

        if key in self._providers:
            raise DuplicateProviderError(str(key))

        registration = ProviderRegistration(key, factory, scope, reloadable)
        self._providers[key] = registration

    def compile(self) -> None:
        """
        Compile all providers - analyze dependencies and build injection plans.

        This must be called before resolving dependencies. It:
        1. Analyzes all provider factories for dependencies
        2. Detects circular dependencies
        3. Validates scope compatibility
        4. Builds injection plans for fast resolution

        Raises:
            CircularDependencyError: If circular dependencies detected
            ScopeMismatchError: If scope rules violated
            ProviderNotFoundError: If required dependency missing
        """
        if self._frozen:
            return

        # Analyze dependencies for each provider
        for registration in self._providers.values():
            self._analyze_dependencies(registration)

        # Detect cycles
        for key in self._providers:
            self._check_cycles(key, [])

        # Validate scope rules
        self._validate_scopes()

        # Build injection plans
        for registration in self._providers.values():
            registration.injection_plan = self._build_injection_plan(registration)

        self._frozen = True

    def get(self, type_: type[T], qualifier: str | None = None) -> T:
        """
        Resolve and return an instance of the requested type.

        Args:
            type_: The type to resolve
            qualifier: Optional qualifier to select specific provider

        Returns:
            Instance of the requested type

        Raises:
            ProviderNotFoundError: If no provider found
        """
        if not self._frozen:
            raise DIError("Container must be compiled before resolving dependencies")

        key = ProviderKey(type_, qualifier)
        registration = self._providers.get(key)

        if registration is None:
            raise ProviderNotFoundError(str(key))

        return self._resolve(registration)

    @contextmanager
    def override(self, overrides: dict[type, ProviderFactory]):
        """
        Temporarily override providers for testing.

        Usage:
            with container.override({Database: lambda: FakeDB()}):
                # Tests run with fake database
                ...
        """
        self._override_stack.append(overrides)
        self._has_active_overrides = True
        try:
            yield
        finally:
            self._override_stack.pop()
            self._has_active_overrides = len(self._override_stack) > 0

    def _analyze_dependencies(self, registration: ProviderRegistration) -> None:
        """Analyze the factory function to extract dependency requirements."""
        try:
            sig = signature(registration.factory)
            hints = get_type_hints(registration.factory, include_extras=True)

            for param_name, param in sig.parameters.items():
                if param_name == "self" or param.annotation == Parameter.empty:
                    continue

                # Get the type hint
                hint = hints.get(param_name, param.annotation)

                # Require type hints for dependency injection
                if hint == Parameter.empty:
                    raise DIError(
                        f"Provider {registration.key} parameter '{param_name}' "
                        f"missing type annotation. All injectable parameters must be typed."
                    )

                # Handle Annotated types for qualifiers
                qualifier = None
                if hasattr(hint, "__metadata__"):
                    for metadata in hint.__metadata__:
                        if isinstance(metadata, Qualifier):
                            qualifier = str(metadata)
                    # Extract the actual type from Annotated
                    hint = hint.__origin__ if hasattr(hint, "__origin__") else hint

                dep_key = ProviderKey(hint, qualifier)
                registration.dependencies.append(dep_key)

        except DIError:
            raise  # Re-raise DI errors
        except Exception as e:
            # Other errors are likely bugs - don't hide them
            raise DIError(
                f"Failed to analyze dependencies for {registration.key}: {e!s}. "
                f"Check that all parameters are properly typed."
            ) from e

    def _check_cycles(self, key: ProviderKey, path: list[ProviderKey]) -> None:
        """Detect circular dependencies via depth-first search."""
        if key in path:
            cycle = [str(k) for k in path[path.index(key) :]]
            raise CircularDependencyError(cycle)

        registration = self._providers.get(key)
        if registration is None:
            return

        new_path = [*path, key]
        for dep_key in registration.dependencies:
            self._check_cycles(dep_key, new_path)

    def _validate_scopes(self) -> None:
        """Validate that scope rules are followed (e.g., singleton can't depend on request)."""
        scope_order = {SINGLETON: 0, Scope.REQUEST: 1, Scope.TASK: 1}

        for key, registration in self._providers.items():
            provider_level = scope_order[registration.scope]

            for dep_key in registration.dependencies:
                dep_registration = self._providers.get(dep_key)
                if dep_registration is None:
                    continue

                dep_level = scope_order[dep_registration.scope]

                # Singleton can't depend on request or task scoped
                if provider_level < dep_level:
                    raise ScopeMismatchError(
                        str(registration.scope),
                        str(dep_registration.scope),
                        str(key),
                    )

    def _build_injection_plan(self, registration: ProviderRegistration) -> Callable:
        """Build a compiled injection plan for fast resolution."""

        def plan() -> Any:
            # Resolve all dependencies
            kwargs = {}
            sig = signature(registration.factory)

            for param_name, dep_key in zip(
                sig.parameters.keys(), registration.dependencies, strict=True
            ):
                dep_registration = self._providers.get(dep_key)
                if dep_registration:
                    kwargs[param_name] = self._resolve(dep_registration)

            # Call factory with resolved dependencies
            return registration.factory(**kwargs)

        return plan

    def _resolve(self, registration: ProviderRegistration) -> Any:
        """Resolve a single provider instance based on its scope."""
        # Fast path: skip override check if no overrides active
        if self._has_active_overrides:
            for override_map in reversed(self._override_stack):
                if registration.key.type in override_map:
                    return override_map[registration.key.type]()

        if registration.scope == SINGLETON:
            # Double-checked locking for thread-safe singleton resolution
            if registration.key not in self._singletons:
                # Get or create lock for this key
                if registration.key not in self._singleton_locks:
                    self._singleton_locks[registration.key] = threading.Lock()

                with self._singleton_locks[registration.key]:
                    # Check again inside lock
                    if registration.key not in self._singletons:
                        assert registration.injection_plan is not None
                        self._singletons[registration.key] = registration.injection_plan()

            return self._singletons[registration.key]

        if registration.scope in (Scope.REQUEST, Scope.TASK):
            # Request/Task: cache in scope bag
            bag = ScopeContext.get_bag_for_scope(registration.scope)
            if bag is None:
                raise DIError(
                    f"Cannot resolve {registration.scope} scoped dependency outside of {registration.scope} context"
                )

            cache_key = str(registration.key)
            if cache_key not in bag:
                assert registration.injection_plan is not None
                bag[cache_key] = registration.injection_plan()
            return bag[cache_key]

        # Transient or unknown: create new instance
        assert registration.injection_plan is not None
        return registration.injection_plan()
