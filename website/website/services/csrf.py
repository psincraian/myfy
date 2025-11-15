"""CSRF token generation and validation service."""

from itsdangerous import BadSignature, URLSafeTimedSerializer

from myfy.core import SINGLETON, provider

from ..config import SecuritySettings


class CsrfService:
    """Service for CSRF token generation and validation.

    This service handles all CSRF-related operations including token
    generation, validation, and management.

    Args:
        settings: Security settings (injected via DI)
    """

    def __init__(self, settings: SecuritySettings):
        """Initialize the CSRF service.

        Args:
            settings: Security settings from DI container
        """
        self.settings = settings
        self.serializer = URLSafeTimedSerializer(self.settings.secret_key, salt="csrf-token")

    def generate_token(self) -> str:
        """Generate a CSRF token.

        Returns:
            CSRF token string
        """
        return self.serializer.dumps("csrf-token")

    def validate_token(self, token: str, max_age: int | None = None) -> bool:
        """Validate a CSRF token.

        Args:
            token: The CSRF token to validate
            max_age: Maximum age of token in seconds (default from settings)

        Returns:
            True if valid, False otherwise
        """
        if max_age is None:
            max_age = self.settings.csrf_max_age

        try:
            self.serializer.loads(token, max_age=max_age)
            return True
        except (BadSignature, Exception):
            return False


@provider(scope=SINGLETON)
def csrf_service(settings: SecuritySettings) -> CsrfService:
    """Provider for CsrfService.

    This function is registered in the DI container and creates a singleton
    instance of CsrfService with the injected security settings.

    Args:
        settings: Security settings (automatically injected by DI)

    Returns:
        CsrfService instance
    """
    return CsrfService(settings)
