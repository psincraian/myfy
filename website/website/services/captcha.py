"""Captcha generation and validation service."""

import secrets

from captcha.image import ImageCaptcha
from itsdangerous import BadSignature, URLSafeTimedSerializer

from myfy.core import SINGLETON, provider

from ..config import SecuritySettings


class CaptchaService:
    """Service for captcha generation and validation.

    This service handles all captcha-related operations including image
    generation, token creation, and solution validation.

    Args:
        settings: Security settings (injected via DI)
    """

    def __init__(self, settings: SecuritySettings):
        """Initialize the captcha service.

        Args:
            settings: Security settings from DI container
        """
        self.settings = settings
        self.serializer = URLSafeTimedSerializer(self.settings.secret_key, salt="captcha")
        self.image_captcha = ImageCaptcha(width=200, height=80, fonts=None)

    def generate_captcha(self) -> tuple[str, bytes]:
        """Generate a captcha challenge.

        Returns:
            Tuple of (captcha_token, captcha_image_bytes)
            - captcha_token: Signed token containing the solution
            - captcha_image_bytes: PNG image data
        """
        # Generate random 6-character captcha text (mix of letters and numbers)
        chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # Exclude confusing characters
        solution = "".join(secrets.choice(chars) for _ in range(6))

        # Generate image
        image_data = self.image_captcha.generate(solution)
        image_bytes = image_data.getvalue()

        # Create signed token with the solution
        token = self.serializer.dumps(solution)

        return token, image_bytes

    def validate_captcha(self, token: str, user_input: str, max_age: int = 300) -> bool:
        """Validate a captcha response.

        Args:
            token: The captcha token containing the solution
            user_input: The user's captcha input
            max_age: Maximum age of token in seconds (default 5 minutes)

        Returns:
            True if valid, False otherwise
        """
        if not token or not user_input:
            return False

        try:
            # Extract solution from token
            solution = self.serializer.loads(token, max_age=max_age)
            # Case-insensitive comparison
            return solution.upper() == user_input.upper().strip()
        except (BadSignature, Exception):
            return False


@provider(scope=SINGLETON)
def captcha_service(settings: SecuritySettings) -> CaptchaService:
    """Provider for CaptchaService.

    This function is registered in the DI container and creates a singleton
    instance of CaptchaService with the injected security settings.

    Args:
        settings: Security settings (automatically injected by DI)

    Returns:
        CaptchaService instance
    """
    return CaptchaService(settings)
