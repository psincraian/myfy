"""
Query parameter definitions for route handlers.

Provides FastAPI-like Query parameter declarations with validation.

Usage:
    @route.get("/api/v2/projects/search")
    async def search_projects(
        q: str = Query(default=""),
        limit: int = Query(default=20, ge=1, le=100),
        service: ProjectSearchService,
    ) -> list[dict]:
        # Parameters are validated and typed automatically
        return await service.search(q, limit)
"""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class QueryParam:
    """
    Query parameter specification with validation constraints.

    Attributes:
        default: Default value if parameter is not provided. Use ... (Ellipsis)
                 or leave unset for required parameters.
        ge: Greater than or equal constraint (for numeric types)
        le: Less than or equal constraint (for numeric types)
        gt: Greater than constraint (for numeric types)
        lt: Less than constraint (for numeric types)
        min_length: Minimum string length
        max_length: Maximum string length
        pattern: Regex pattern for string validation
        description: Parameter description for documentation
        alias: Alternative name to use when extracting from query string
    """

    default: Any = ...  # Ellipsis means required
    ge: float | int | None = None
    le: float | int | None = None
    gt: float | int | None = None
    lt: float | int | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    description: str | None = None
    alias: str | None = None

    @property
    def is_required(self) -> bool:
        """Check if this parameter is required."""
        return self.default is ...

    def validate(self, value: Any, param_name: str) -> Any:
        """
        Validate the value against constraints.

        Args:
            value: The value to validate
            param_name: Parameter name for error messages

        Returns:
            The validated value

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            if self.is_required:
                raise ValueError(f"Query parameter '{param_name}' is required")
            return self.default

        # Numeric constraints
        if isinstance(value, (int, float)):
            if self.ge is not None and value < self.ge:
                raise ValueError(
                    f"Query parameter '{param_name}' must be >= {self.ge}, got {value}"
                )
            if self.le is not None and value > self.le:
                raise ValueError(
                    f"Query parameter '{param_name}' must be <= {self.le}, got {value}"
                )
            if self.gt is not None and value <= self.gt:
                raise ValueError(f"Query parameter '{param_name}' must be > {self.gt}, got {value}")
            if self.lt is not None and value >= self.lt:
                raise ValueError(f"Query parameter '{param_name}' must be < {self.lt}, got {value}")

        # String constraints
        if isinstance(value, str):
            if self.min_length is not None and len(value) < self.min_length:
                raise ValueError(
                    f"Query parameter '{param_name}' must have at least {self.min_length} characters"
                )
            if self.max_length is not None and len(value) > self.max_length:
                raise ValueError(
                    f"Query parameter '{param_name}' must have at most {self.max_length} characters"
                )
            if self.pattern is not None and not re.match(self.pattern, value):
                raise ValueError(
                    f"Query parameter '{param_name}' must match pattern '{self.pattern}'"
                )

        return value


def Query(  # noqa: N802 - FastAPI-style naming convention
    default: Any = ...,
    *,
    ge: float | int | None = None,
    le: float | int | None = None,
    gt: float | int | None = None,
    lt: float | int | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    pattern: str | None = None,
    description: str | None = None,
    alias: str | None = None,
) -> Any:
    """
    Declare a query parameter with optional validation constraints.

    This function returns a QueryParam instance that the routing system
    uses to extract and validate query parameters from requests.

    Args:
        default: Default value if parameter is not provided.
                 Use ... (Ellipsis) for required parameters.
        ge: Greater than or equal constraint (for int/float)
        le: Less than or equal constraint (for int/float)
        gt: Greater than constraint (for int/float)
        lt: Less than constraint (for int/float)
        min_length: Minimum string length
        max_length: Maximum string length
        pattern: Regex pattern for string validation
        description: Parameter description for documentation
        alias: Alternative name to use when extracting from query string

    Returns:
        A QueryParam specification object

    Examples:
        # Required string parameter
        q: str = Query()

        # Optional parameter with default
        limit: int = Query(default=20)

        # Validated numeric parameter
        page: int = Query(default=1, ge=1, le=1000)

        # String with length constraints
        search: str = Query(default="", min_length=1, max_length=100)
    """
    return QueryParam(
        default=default,
        ge=ge,
        le=le,
        gt=gt,
        lt=lt,
        min_length=min_length,
        max_length=max_length,
        pattern=pattern,
        description=description,
        alias=alias,
    )


@dataclass
class QueryParamInfo:
    """
    Stores information about a query parameter for a route.

    This is used internally by the routing system to track
    which parameters are query parameters and their specifications.
    """

    name: str
    type_hint: type
    spec: QueryParam
    alias: str | None = None

    @property
    def query_name(self) -> str:
        """Get the name to use when extracting from query string."""
        return self.alias or self.name
