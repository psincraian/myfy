"""
Registry for protected types and their status codes.
"""

from dataclasses import dataclass


@dataclass
class ProtectedTypesRegistry:
    """
    Registry mapping types to HTTP status codes.

    When a protected type's provider returns None,
    the framework returns the configured status code.

    Example::

        registry = ProtectedTypesRegistry({
            Authenticated: 401,
            AdminUser: 403,
        })

        # Check if User (subclass of Authenticated) is protected
        code = registry.get_status_code(User)  # Returns 401
    """

    types: dict[type, int]

    def get_status_code(self, typ: type) -> int | None:
        """
        Get status code for a type, checking inheritance.

        Checks both direct matches and inheritance. More specific
        types (subclasses) are checked first via direct match.

        Args:
            typ: The type to check

        Returns:
            Status code if type is protected, None otherwise
        """
        if typ is None:
            return None

        # Direct match first (most specific)
        if typ in self.types:
            return self.types[typ]

        # Check inheritance (less specific)
        for protected_type, code in self.types.items():
            if isinstance(typ, type) and issubclass(typ, protected_type):
                return code

        return None

    def get_error_detail(self, status_code: int) -> str:
        """
        Get error message for status code.

        Args:
            status_code: HTTP status code

        Returns:
            Human-readable error message
        """
        return {
            401: "Authentication required",
            403: "Forbidden",
        }.get(status_code, "Access denied")
