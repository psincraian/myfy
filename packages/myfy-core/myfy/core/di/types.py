"""
Type definitions and protocols for the DI system.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, TypedDict, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from .scopes import Scope

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class Qualifier(str):
    """
    A qualifier for distinguishing multiple providers of the same type.

    Usage:
        ReadDB = Annotated[Database, Qualifier("read")]
        WriteDB = Annotated[Database, Qualifier("write")]
    """


@runtime_checkable
class Provider(Protocol):
    """Protocol for a provider factory function."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Create an instance of the dependency."""
        ...


# Type alias for provider factories
ProviderFactory = Callable[..., T]


class ProviderMetadata(TypedDict):
    """Metadata stored for each @provider decorated function."""

    factory: Callable[..., Any]
    scope: "Scope"
    qualifier: str | None
    name: str | None
    reloadable: tuple[str, ...]


class ProviderKey:
    """
    Unique key for identifying a provider in the container.

    Combines type, optional qualifier, and optional name for resolution.
    """

    def __init__(
        self,
        type_: type,
        qualifier: str | None = None,
        name: str | None = None,
    ):
        self.type = type_
        self.qualifier = qualifier
        self.name = name

    def __hash__(self) -> int:
        return hash((self.type, self.qualifier, self.name))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProviderKey):
            return False
        return (
            self.type == other.type
            and self.qualifier == other.qualifier
            and self.name == other.name
        )

    def __repr__(self) -> str:
        parts = [self.type.__name__]
        if self.qualifier:
            parts.append(f'qualifier="{self.qualifier}"')
        if self.name:
            parts.append(f'name="{self.name}"')
        return f"ProviderKey({', '.join(parts)})"
