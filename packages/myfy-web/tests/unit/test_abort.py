"""
Unit tests for the abort() shortcut function.

These tests verify:
- abort() raises the correct exception type for each status code
- Default messages are used when none provided
- Extra fields are passed through
- Unknown status codes fall back to WebError
"""

import pytest

from myfy.web.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    UnauthorizedError,
    UnprocessableEntityError,
    ValidationError,
    WebError,
)
from myfy.web.shortcuts import abort

pytestmark = pytest.mark.unit


# =============================================================================
# Status Code Mapping Tests
# =============================================================================


class TestStatusCodeMapping:
    """Verify abort() raises the correct exception type for each status code."""

    @pytest.mark.parametrize(
        ("status_code", "expected_class"),
        [
            (400, ValidationError),
            (401, UnauthorizedError),
            (403, ForbiddenError),
            (404, NotFoundError),
            (409, ConflictError),
            (422, UnprocessableEntityError),
            (429, RateLimitError),
            (503, ServiceUnavailableError),
        ],
    )
    def test_abort_raises_correct_exception_type(self, status_code, expected_class):
        """abort() raises the correct exception class for each status code."""
        with pytest.raises(expected_class) as exc_info:
            abort(status_code, "Test message")

        assert exc_info.value.status_code == status_code

    def test_abort_unknown_status_raises_web_error(self):
        """Unknown status codes fall back to WebError with overridden status."""
        with pytest.raises(WebError) as exc_info:
            abort(418, "I'm a teapot")

        error = exc_info.value
        assert error.status_code == 418
        assert str(error) == "I'm a teapot"


# =============================================================================
# Message Handling Tests
# =============================================================================


class TestMessageHandling:
    """Verify message handling in abort()."""

    def test_abort_with_custom_message(self):
        """Custom message is used when provided."""
        with pytest.raises(NotFoundError) as exc_info:
            abort(404, "User not found")

        assert str(exc_info.value) == "User not found"

    def test_abort_with_default_message(self):
        """Default message is used when none provided."""
        with pytest.raises(NotFoundError) as exc_info:
            abort(404)

        assert str(exc_info.value) == "Not Found"

    @pytest.mark.parametrize(
        ("status_code", "expected_default"),
        [
            (400, "Bad Request"),
            (401, "Unauthorized"),
            (403, "Forbidden"),
            (404, "Not Found"),
            (409, "Conflict"),
            (422, "Unprocessable Entity"),
            (429, "Too Many Requests"),
            (500, "Internal Server Error"),
            (503, "Service Unavailable"),
        ],
    )
    def test_default_messages_for_known_codes(self, status_code, expected_default):
        """Each known status code has an appropriate default message."""
        with pytest.raises(WebError) as exc_info:
            abort(status_code)

        assert str(exc_info.value) == expected_default

    def test_unknown_status_code_default_message(self):
        """Unknown status codes use generic default message."""
        with pytest.raises(WebError) as exc_info:
            abort(418)

        assert str(exc_info.value) == "An error occurred"


# =============================================================================
# Extra Fields Tests
# =============================================================================


class TestExtraFields:
    """Verify extra fields are passed through abort()."""

    def test_abort_with_extra_fields(self):
        """Extra fields are included in the exception."""
        with pytest.raises(ValidationError) as exc_info:
            abort(400, "Invalid email", field="email", provided="not-an-email")

        error = exc_info.value
        assert error.extra["field"] == "email"
        assert error.extra["provided"] == "not-an-email"

    def test_abort_extra_fields_in_problem_detail(self):
        """Extra fields appear in Problem Details output."""
        with pytest.raises(NotFoundError) as exc_info:
            abort(404, "User not found", user_id=123)

        detail = exc_info.value.to_problem_detail()
        assert detail["user_id"] == 123

    def test_abort_with_no_extra_fields(self):
        """abort() works correctly with no extra fields."""
        with pytest.raises(ForbiddenError) as exc_info:
            abort(403, "Access denied")

        assert exc_info.value.extra == {}


# =============================================================================
# NoReturn Type Tests
# =============================================================================


class TestNoReturn:
    """Verify abort() never returns (always raises)."""

    def test_abort_always_raises(self):
        """abort() always raises an exception, never returns."""
        raised = False
        try:
            abort(500, "Error")
        except WebError:
            raised = True

        assert raised, "abort() should always raise"

    def test_abort_can_be_used_in_conditional(self):
        """abort() can be used as a terminal statement in conditionals."""

        def get_user(user_id: int | None) -> dict:
            if user_id is None:
                abort(400, "user_id is required")
            # Type checker should understand we never reach here if user_id is None
            return {"id": user_id}

        # Valid call
        result = get_user(123)
        assert result["id"] == 123

        # Invalid call
        with pytest.raises(ValidationError):
            get_user(None)
