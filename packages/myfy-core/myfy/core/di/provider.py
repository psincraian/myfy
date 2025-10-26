"""
Provider decorator for ergonomic dependency registration.

This is the "sugar" layer over the explicit container.register() API.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, get_type_hints

from .scopes import SINGLETON, Scope
from .types import Qualifier

T = TypeVar("T")

# Global registry for providers decorated before container is created
_pending_providers: list[tuple[Callable, dict[str, Any]]] = []


def provider(
    scope: Scope = SINGLETON,
    qualifier: str | None = None,
    name: str | None = None,
    reloadable: tuple[str, ...] = (),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to register a function as a dependency provider.

    The decorated function will be registered in the container during
    application startup. The return type annotation is used as the
    provided type.

    Usage:
        @provider(scope=SINGLETON)
        def database(settings: Settings) -> Database:
            return Database(settings.db_url)

        @provider(scope=REQUEST)
        def unit_of_work(db: Database) -> UnitOfWork:
            return UnitOfWork(db)

    Args:
        scope: Lifecycle scope (default: SINGLETON)
        qualifier: Optional qualifier for multiple providers of same type
        name: Optional name for resolution
        reloadable: Tuple of settings that can be hot-reloaded

    Returns:
        Decorator that registers the provider
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Store provider metadata for later registration
        metadata = {
            "factory": func,
            "scope": scope,
            "qualifier": qualifier,
            "name": name,
            "reloadable": reloadable,
        }
        _pending_providers.append((func, metadata))

        # Mark the function with metadata (useful for introspection)
        func.__myfy_provider__ = metadata  # type: ignore

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # During normal calls, just execute the function
            # (The container will handle injection)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_pending_providers() -> list[tuple[Callable, dict[str, Any]]]:
    """
    Get all providers that have been decorated but not yet registered.

    This is called by the application kernel during startup to register
    all @provider decorated functions.
    """
    return _pending_providers.copy()


def clear_pending_providers() -> None:
    """Clear the pending providers registry (useful for testing)."""
    _pending_providers.clear()


def register_providers_in_container(container: Any) -> None:
    """
    Register all pending providers in the given container.

    This is called automatically during application startup.

    Args:
        container: The Container instance to register providers in
    """
    for func, metadata in _pending_providers:
        # Extract return type from function annotations
        hints = get_type_hints(func)
        return_type = hints.get("return")

        if return_type is None:
            func_name = getattr(func, "__name__", "<unknown>")
            raise TypeError(f"Provider function {func_name} must have a return type annotation")

        # Handle Annotated return types
        if hasattr(return_type, "__metadata__"):
            # Check for Qualifier in metadata
            for meta in return_type.__metadata__:
                if isinstance(meta, Qualifier) and metadata["qualifier"] is None:
                    metadata["qualifier"] = str(meta)
            # Extract actual type
            return_type = (
                return_type.__origin__ if hasattr(return_type, "__origin__") else return_type
            )

        container.register(
            type_=return_type,
            factory=metadata["factory"],
            scope=metadata["scope"],
            qualifier=metadata["qualifier"],
            name=metadata["name"],
            reloadable=metadata["reloadable"],
        )

    # Clear after registration to avoid double-registration
    clear_pending_providers()
