"""
Email service interface for sending emails.

This provides a protocol that users can implement with their preferred
email provider (SMTP, SendGrid, AWS SES, etc.).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmailService(Protocol):
    """
    Protocol for email sending services.

    Implement this protocol to integrate your preferred email provider.

    Example:
        ```python
        class SMTPEmailService:
            def __init__(self, host: str, port: int, username: str, password: str):
                self.host = host
                self.port = port
                self.username = username
                self.password = password

            async def send_email(
                self,
                to: str,
                subject: str,
                body: str,
                html: str | None = None,
            ) -> None:
                # Send via SMTP
                ...

        # Register in DI
        @provider(scope=SINGLETON)
        def email_service() -> EmailService:
            return SMTPEmailService(...)
        ```
    """

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: str | None = None,
    ) -> None:
        """
        Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Plain text body
            html: Optional HTML body
        """
        ...


class ConsoleEmailService:
    """
    Development email service that prints to console.

    Useful for development and testing.
    """

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: str | None = None,
    ) -> None:
        """Print email to console."""
        print(f"\n{'=' * 60}")
        print(f"EMAIL TO: {to}")
        print(f"SUBJECT: {subject}")
        print(f"{'-' * 60}")
        print(body)
        if html:
            print(f"{'-' * 60}")
            print("HTML body provided (not shown)")
        print(f"{'=' * 60}\n")


class NoOpEmailService:
    """
    No-op email service that does nothing.

    Useful for testing when you don't want console output.
    """

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: str | None = None,
    ) -> None:
        """Do nothing."""


class EmailTemplates:
    """
    Helper class for generating email content.

    Usage:
        ```python
        templates = EmailTemplates(base_url="https://myapp.com")

        subject, body, html = templates.verification_email(
            user_email="user@example.com",
            token="abc123",
        )
        ```
    """

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        """
        Initialize email templates.

        Args:
            base_url: Base URL of the application
        """
        self.base_url = base_url.rstrip("/")

    def verification_email(
        self,
        user_email: str,  # noqa: ARG002 - Reserved for personalization
        token: str,
    ) -> tuple[str, str, str]:
        """
        Generate email verification email content.

        Args:
            user_email: User's email address
            token: Verification token

        Returns:
            Tuple of (subject, body, html)
        """
        verification_url = f"{self.base_url}/verify-email/{token}"

        subject = "Verify your email address"

        body = f"""Hello,

Please verify your email address by clicking the link below:

{verification_url}

This link will expire in 24 hours.

If you did not create an account, you can ignore this email.

Thanks,
The Team
"""

        html = f"""
<html>
<body>
<p>Hello,</p>
<p>Please verify your email address by clicking the link below:</p>
<p><a href="{verification_url}">Verify Email Address</a></p>
<p>Or copy and paste this URL into your browser:</p>
<p>{verification_url}</p>
<p>This link will expire in 24 hours.</p>
<p>If you did not create an account, you can ignore this email.</p>
<p>Thanks,<br>The Team</p>
</body>
</html>
"""

        return subject, body, html

    def password_reset_email(
        self,
        user_email: str,  # noqa: ARG002 - Reserved for personalization
        token: str,
    ) -> tuple[str, str, str]:
        """
        Generate password reset email content.

        Args:
            user_email: User's email address
            token: Reset token

        Returns:
            Tuple of (subject, body, html)
        """
        reset_url = f"{self.base_url}/reset-password/{token}"

        subject = "Reset your password"

        body = f"""Hello,

You requested to reset your password. Click the link below to set a new password:

{reset_url}

This link will expire in 1 hour.

If you did not request a password reset, you can ignore this email.

Thanks,
The Team
"""

        html = f"""
<html>
<body>
<p>Hello,</p>
<p>You requested to reset your password. Click the link below to set a new password:</p>
<p><a href="{reset_url}">Reset Password</a></p>
<p>Or copy and paste this URL into your browser:</p>
<p>{reset_url}</p>
<p>This link will expire in 1 hour.</p>
<p>If you did not request a password reset, you can ignore this email.</p>
<p>Thanks,<br>The Team</p>
</body>
</html>
"""

        return subject, body, html

    def welcome_email(
        self,
        user_email: str,
        display_name: str | None = None,
    ) -> tuple[str, str, str]:
        """
        Generate welcome email content.

        Args:
            user_email: User's email address
            display_name: User's display name

        Returns:
            Tuple of (subject, body, html)
        """
        name = display_name or user_email.split("@")[0]

        subject = "Welcome!"

        body = f"""Hello {name},

Welcome! Your account has been created successfully.

You can now log in at: {self.base_url}/login

Thanks,
The Team
"""

        html = f"""
<html>
<body>
<p>Hello {name},</p>
<p>Welcome! Your account has been created successfully.</p>
<p>You can now <a href="{self.base_url}/login">log in</a>.</p>
<p>Thanks,<br>The Team</p>
</body>
</html>
"""

        return subject, body, html
