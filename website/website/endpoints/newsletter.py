"""Newsletter subscription endpoints."""

import logging
from datetime import UTC, datetime

from email_validator import EmailNotValidError, validate_email
from itsdangerous import BadSignature, URLSafeTimedSerializer
from starlette.requests import Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from myfy.frontend import render_template
from myfy.web import route

from ..services import CaptchaService, NewsletterService
from ..services.csrf import CsrfService

logger = logging.getLogger(__name__)


@route.get("/newsletter")
async def newsletter_page(
    request: Request, templates: Jinja2Templates, captcha_service: CaptchaService
):
    """Newsletter signup page.

    Args:
        request: HTTP request
        templates: Jinja2 templates (DI-injected)
        captcha_service: Captcha service (DI-injected)

    Returns:
        Rendered newsletter page template
    """
    # Generate captcha token for the form
    captcha_token, _ = captcha_service.generate_captcha()

    return render_template(
        "newsletter.html",
        request=request,
        templates=templates,
        current_year=datetime.now(tz=UTC).year,
        success=False,
        error=False,
        captcha_token=captcha_token,
    )


@route.post("/newsletter")
async def newsletter_subscribe(
    request: Request,
    templates: Jinja2Templates,
    service: NewsletterService,
    csrf_service: CsrfService,
    captcha_service: CaptchaService,
):
    """Handle newsletter subscription form submission.

    This endpoint:
    1. Validates CSRF token
    2. Validates captcha
    3. Validates email format and length
    4. Subscribes email via NewsletterService
    5. Returns success/error page

    Args:
        request: HTTP request
        templates: Jinja2 templates (DI-injected)
        service: Newsletter service (DI-injected)
        csrf_service: CSRF service for token validation (DI-injected)
        captcha_service: Captcha service for captcha validation (DI-injected)

    Returns:
        Rendered newsletter page with success/error message
    """
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"Newsletter subscription attempt from {client_host}")

    # Parse form data
    form_data = await request.form()
    email_raw = form_data.get("email", "")
    csrf_token_raw = form_data.get("csrf_token", "")
    captcha_token_raw = form_data.get("captcha_token", "")
    captcha_input_raw = form_data.get("captcha_input", "")

    # Ensure we have strings, not UploadFile
    email = email_raw if isinstance(email_raw, str) else ""
    csrf_token = csrf_token_raw if isinstance(csrf_token_raw, str) else ""
    captcha_token = captcha_token_raw if isinstance(captcha_token_raw, str) else ""
    captcha_input = captcha_input_raw if isinstance(captcha_input_raw, str) else ""

    email = email.strip()
    csrf_token = csrf_token.strip()
    captcha_token = captcha_token.strip()
    captcha_input = captcha_input.strip()

    # Helper function to render error with new captcha
    def render_error(message: str):
        new_captcha_token, _ = captcha_service.generate_captcha()
        return render_template(
            "newsletter.html",
            request=request,
            templates=templates,
            current_year=datetime.now(tz=UTC).year,
            success=False,
            error=True,
            message=message,
            captcha_token=new_captcha_token,
        )

    # Validate CSRF token
    if not csrf_token or not csrf_service.validate_token(csrf_token):
        logger.warning(f"CSRF validation failed for newsletter subscription from {client_host}")
        return render_error("Security validation failed. Please try again.")

    # Validate captcha
    if not captcha_service.validate_captcha(captcha_token, captcha_input):
        logger.warning(f"Captcha validation failed for newsletter subscription from {client_host}")
        return render_error("Captcha validation failed. Please try again.")

    # Validate email is provided
    if not email:
        return render_error("Please provide an email address.")

    # Validate email length
    if len(email) > 255:
        return render_error("Email address is too long.")

    # Validate email format using email-validator library
    try:
        valid = validate_email(email, check_deliverability=False)
        email = valid.normalized  # Use normalized form
    except EmailNotValidError:
        logger.warning(f"Invalid email format attempt: {email}")
        return render_error("Please provide a valid email address.")

    # Subscribe via service (business logic handled in service layer)
    success, message = await service.subscribe(email)

    if success:
        logger.info(f"Newsletter subscription successful for {email}")
    else:
        logger.warning(f"Newsletter subscription failed for {email}: {message}")

    # Generate new captcha for next attempt
    new_captcha_token, _ = captcha_service.generate_captcha()

    return render_template(
        "newsletter.html",
        request=request,
        templates=templates,
        current_year=datetime.now(tz=UTC).year,
        success=success,
        error=not success,
        message=message,
        captcha_token=new_captcha_token,
    )


@route.get("/captcha/{token}")
async def captcha_image(token: str, captcha_service: CaptchaService):
    """Generate and serve a captcha image.

    Args:
        token: The captcha token containing the solution
        captcha_service: Captcha service (DI-injected)

    Returns:
        PNG image response
    """
    # Generate new captcha image with the same token
    # We need to extract the solution from the token and regenerate the image
    try:
        # Decode the token to get the solution
        serializer = URLSafeTimedSerializer(captcha_service.settings.secret_key, salt="captcha")
        solution = serializer.loads(token, max_age=300)

        # Generate image with this solution
        image_data = captcha_service.image_captcha.generate(solution)
        image_bytes = image_data.getvalue()

        return Response(
            content=image_bytes,
            media_type="image/png",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    except (BadSignature, Exception) as e:
        logger.warning(f"Invalid captcha token request: {e}")
        # Return a blank/error image or 404
        return Response(status_code=404)
