"""
Unit tests for WebError exception contract.

These tests verify:
- WebError produces valid RFC 7807 Problem Details format
- All built-in exceptions have correct defaults
- Inheritance works correctly for custom exceptions
- Extra fields are preserved in Problem Details output
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

pytestmark = pytest.mark.unit


# =============================================================================
# Built-in Exception Defaults Tests
# =============================================================================


class TestBuiltinExceptionDefaults:
    """Verify each built-in error class has correct status_code and error_type."""

    @pytest.mark.parametrize(
        ("error_class", "expected_status", "expected_type"),
        [
            (WebError, 500, "about:blank"),
            (ValidationError, 400, "validation_error"),
            (UnauthorizedError, 401, "unauthorized"),
            (ForbiddenError, 403, "forbidden"),
            (NotFoundError, 404, "not_found"),
            (ConflictError, 409, "conflict"),
            (UnprocessableEntityError, 422, "unprocessable_entity"),
            (RateLimitError, 429, "rate_limit_exceeded"),
            (ServiceUnavailableError, 503, "service_unavailable"),
        ],
    )
    def test_builtin_errors_have_correct_defaults(
        self, error_class, expected_status, expected_type
    ):
        """Each built-in error class has correct status_code and error_type."""
        error = error_class("Test message")

        assert error.status_code == expected_status
        assert error.error_type == expected_type


# =============================================================================
# Problem Details Format Tests
# =============================================================================


class TestProblemDetailFormat:
    """Verify to_problem_detail() produces valid RFC 7807 format."""

    def test_problem_detail_contains_required_fields(self):
        """to_problem_detail() includes all RFC 7807 recommended fields."""
        error = NotFoundError("User not found")
        detail = error.to_problem_detail()

        # RFC 7807 recommended fields
        assert "type" in detail
        assert "title" in detail
        assert "status" in detail
        assert "detail" in detail

        # Values are correct
        assert detail["type"] == "not_found"
        assert detail["title"] == "NotFoundError"
        assert detail["status"] == 404
        assert detail["detail"] == "User not found"

    def test_extra_fields_included_in_problem_detail(self):
        """Extra kwargs are included in Problem Details output."""
        error = ValidationError(
            "Invalid email format",
            field="email",
            provided_value="not-an-email",
        )
        detail = error.to_problem_detail()

        assert detail["field"] == "email"
        assert detail["provided_value"] == "not-an-email"

    def test_multiple_extra_fields(self):
        """Multiple extra fields are all preserved."""
        error = ConflictError(
            "Duplicate entry",
            resource="user",
            field="username",
            value="john_doe",
            existing_id=123,
        )
        detail = error.to_problem_detail()

        assert detail["resource"] == "user"
        assert detail["field"] == "username"
        assert detail["value"] == "john_doe"
        assert detail["existing_id"] == 123

    def test_problem_detail_with_no_extra_fields(self):
        """Problem Details works correctly with no extra fields."""
        error = ForbiddenError("Access denied")
        detail = error.to_problem_detail()

        # Should have exactly 4 fields (type, title, status, detail)
        assert len(detail) == 4
        assert detail["type"] == "forbidden"
        assert detail["title"] == "ForbiddenError"
        assert detail["status"] == 403
        assert detail["detail"] == "Access denied"


# =============================================================================
# Inheritance Tests
# =============================================================================


class TestInheritance:
    """Verify user-defined subclasses inherit behavior correctly."""

    def test_subclass_inherits_to_problem_detail(self):
        """User-defined subclasses get to_problem_detail() for free."""

        class PaymentRequiredError(WebError):
            status_code = 402
            error_type = "payment_required"

        error = PaymentRequiredError("Insufficient credits", required=100)
        detail = error.to_problem_detail()

        assert detail["status"] == 402
        assert detail["type"] == "payment_required"
        assert detail["title"] == "PaymentRequiredError"
        assert detail["required"] == 100

    def test_subclass_of_builtin_error(self):
        """Subclassing built-in errors works correctly."""

        class EmailValidationError(ValidationError):
            error_type = "email_validation_error"

        error = EmailValidationError("Invalid email", field="email")
        detail = error.to_problem_detail()

        # Inherits status_code from ValidationError
        assert detail["status"] == 400
        # Uses overridden error_type
        assert detail["type"] == "email_validation_error"
        assert detail["title"] == "EmailValidationError"
        assert detail["field"] == "email"

    def test_deeply_nested_inheritance(self):
        """Multi-level inheritance preserves behavior."""

        class DomainError(WebError):
            status_code = 400
            error_type = "domain_error"

        class UserError(DomainError):
            error_type = "user_error"

        class UserNotFoundError(UserError):
            status_code = 404
            error_type = "user_not_found"

        error = UserNotFoundError("User 123 not found", user_id=123)
        detail = error.to_problem_detail()

        assert detail["status"] == 404
        assert detail["type"] == "user_not_found"
        assert detail["title"] == "UserNotFoundError"
        assert detail["user_id"] == 123


# =============================================================================
# String Representation Tests
# =============================================================================


class TestStringRepresentation:
    """Verify exception message is accessible via str()."""

    def test_error_message_accessible_via_str(self):
        """Exception message is accessible via str() for logging."""
        error = NotFoundError("Project 'foo' not found")

        assert str(error) == "Project 'foo' not found"

    def test_error_with_special_characters(self):
        """Messages with special characters are preserved."""
        error = ValidationError("Field 'email' must contain '@' character")

        assert str(error) == "Field 'email' must contain '@' character"

    def test_empty_message(self):
        """Empty message is valid."""
        error = WebError("")

        assert str(error) == ""
        assert error.to_problem_detail()["detail"] == ""


# =============================================================================
# Instance Override Tests
# =============================================================================


class TestInstanceOverrides:
    """Verify status_code can be overridden per instance."""

    def test_status_code_can_be_overridden_per_instance(self):
        """Status code can be overridden on instance if needed."""
        error = WebError("Custom error")
        error.status_code = 418  # I'm a teapot

        detail = error.to_problem_detail()
        assert detail["status"] == 418

    def test_error_type_can_be_overridden_per_instance(self):
        """Error type can be overridden on instance."""
        error = WebError("Custom error")
        error.error_type = "custom_error"

        detail = error.to_problem_detail()
        assert detail["type"] == "custom_error"


# =============================================================================
# Extra Field Edge Cases
# =============================================================================


class TestExtraFieldEdgeCases:
    """Test edge cases with extra fields."""

    def test_extra_field_with_none_value(self):
        """None values in extra fields are preserved."""
        error = NotFoundError("Not found", optional_field=None)
        detail = error.to_problem_detail()

        assert "optional_field" in detail
        assert detail["optional_field"] is None

    def test_extra_field_with_complex_types(self):
        """Complex types (lists, dicts) in extra fields are preserved."""
        error = ValidationError(
            "Multiple errors",
            errors=[{"field": "email", "msg": "invalid"}, {"field": "name", "msg": "required"}],
            metadata={"request_id": "abc123"},
        )
        detail = error.to_problem_detail()

        assert len(detail["errors"]) == 2
        assert detail["errors"][0]["field"] == "email"
        assert detail["metadata"]["request_id"] == "abc123"

    def test_extra_attribute_accessible(self):
        """Extra fields are accessible via .extra attribute."""
        error = ConflictError("Conflict", field="username", value="john")

        assert error.extra["field"] == "username"
        assert error.extra["value"] == "john"
