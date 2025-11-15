"""Newsletter subscription endpoints."""

import logging
from datetime import UTC, datetime

from email_validator import EmailNotValidError, validate_email
from starlette.requests import Request
from starlette.templating import Jinja2Templates

from myfy.frontend import render_template
from myfy.web import route

from ..modules.security import SecurityModule
from ..services import NewsletterService

logger = logging.getLogger(__name__)


@route.get("/newsletter")
async def newsletter_page(request: Request, templates: Jinja2Templates):
    """Newsletter signup page.

    Args:
        request: HTTP request
        templates: Jinja2 templates (DI-injected)

    Returns:
        Rendered newsletter page template
    """
    return render_template(
        "newsletter.html",
        request=request,
        templates=templates,
        current_year=datetime.now(tz=UTC).year,
        success=False,
        error=False,
    )


@route.post("/newsletter")
async def newsletter_subscribe(
    request: Request,
    templates: Jinja2Templates,
    service: NewsletterService,
    security_module: SecurityModule,
):
    """Handle newsletter subscription form submission.

    This endpoint:
    1. Validates CSRF token
    2. Validates email format and length
    3. Subscribes email via NewsletterService
    4. Returns success/error page

    Args:
        request: HTTP request
        templates: Jinja2 templates (DI-injected)
        service: Newsletter service (DI-injected)
        security_module: Security module for CSRF validation (DI-injected)

    Returns:
        Rendered newsletter page with success/error message
    """
    logger.info(f"Newsletter subscription attempt from {request.client.host}")

    # Parse form data
    form_data = await request.form()
    email = form_data.get("email", "").strip()
    csrf_token = form_data.get("csrf_token", "").strip()

    # Validate CSRF token
    if not csrf_token or not security_module.validate_csrf_token(csrf_token):
        logger.warning(
            f"CSRF validation failed for newsletter subscription from {request.client.host}"
        )
        return render_template(
            "newsletter.html",
            request=request,
            templates=templates,
            current_year=datetime.now(tz=UTC).year,
            success=False,
            error=True,
            message="Security validation failed. Please try again.",
        )

    # Validate email is provided
    if not email:
        return render_template(
            "newsletter.html",
            request=request,
            templates=templates,
            current_year=datetime.now(tz=UTC).year,
            success=False,
            error=True,
            message="Please provide an email address.",
        )

    # Validate email length
    if len(email) > 255:
        return render_template(
            "newsletter.html",
            request=request,
            templates=templates,
            current_year=datetime.now(tz=UTC).year,
            success=False,
            error=True,
            message="Email address is too long.",
        )

    # Validate email format using email-validator library
    try:
        valid = validate_email(email, check_deliverability=False)
        email = valid.normalized  # Use normalized form
    except EmailNotValidError:
        logger.warning(f"Invalid email format attempt: {email}")
        return render_template(
            "newsletter.html",
            request=request,
            templates=templates,
            current_year=datetime.now(tz=UTC).year,
            success=False,
            error=True,
            message="Please provide a valid email address.",
        )

    # Subscribe via service (business logic handled in service layer)
    success, message = await service.subscribe(email)

    if success:
        logger.info(f"Newsletter subscription successful for {email}")
    else:
        logger.warning(f"Newsletter subscription failed for {email}: {message}")

    return render_template(
        "newsletter.html",
        request=request,
        templates=templates,
        current_year=datetime.now(tz=UTC).year,
        success=success,
        error=not success,
        message=message,
    )
