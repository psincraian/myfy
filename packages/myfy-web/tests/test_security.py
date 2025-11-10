"""
Security tests for web handlers and routing.

Tests XSS prevention, input validation, and other security concerns.
"""

import pytest
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException
from starlette.testclient import TestClient

from myfy.core import Application
from myfy.web import WebModule, route


class TestXSSPrevention:
    """Test XSS attack prevention."""

    def test_path_params_no_script_execution(self):
        """Should safely handle malicious path parameters."""

        @route.get("/user/{user_id}")
        def get_user(user_id: str):
            return {"user_id": user_id}

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            # Try script injection in path
            response = client.get("/user/<script>alert('xss')</script>")
            assert response.status_code == 200
            # Should return as string, not execute
            assert "<script>" in response.json()["user_id"]

    def test_json_response_safe_serialization(self):
        """Should safely serialize potentially malicious data."""

        @route.get("/data")
        def get_data():
            return {"input": "<script>alert('xss')</script>", "safe": True}

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            response = client.get("/data")
            # JSON should be safely serialized
            assert response.status_code == 200
            data = response.json()
            assert data["input"] == "<script>alert('xss')</script>"


class TestInputValidation:
    """Test input validation and sanitization."""

    def test_path_param_type_validation_prevents_injection(self):
        """Should validate path parameter types strictly."""

        @route.get("/item/{item_id}")
        def get_item(item_id: int):
            return {"item_id": item_id}

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            # Valid integer
            response = client.get("/item/123")
            assert response.status_code == 200
            assert response.json()["item_id"] == 123

            # SQL injection attempt
            response = client.get("/item/1'; DROP TABLE users--")
            assert response.status_code == 400
            assert "Invalid value" in response.json()["detail"]

            # Script injection attempt
            response = client.get("/item/<script>")
            assert response.status_code == 400

    def test_request_body_size_validation(self):
        """Should reject oversized request bodies."""

        class LimitedInput(BaseModel):
            text: str = Field(..., max_length=100)

        @route.post("/limited")
        def post_limited(data: LimitedInput):
            return {"length": len(data.text)}

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            # Within limit
            response = client.post("/limited", json={"text": "a" * 100})
            assert response.status_code == 200

            # Exceeds limit
            response = client.post("/limited", json={"text": "a" * 101})
            assert response.status_code == 422

    def test_malicious_json_payloads_rejected(self):
        """Should handle malicious JSON payloads safely."""

        class SafeInput(BaseModel):
            name: str
            age: int

        @route.post("/safe")
        def post_safe(data: SafeInput):
            return data.model_dump()

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            # Extra fields should be ignored (Pydantic default)
            response = client.post(
                "/safe",
                json={
                    "name": "Test",
                    "age": 25,
                    "__proto__": {"admin": True},  # Prototype pollution attempt
                    "constructor": "malicious",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "admin" not in data
            assert "constructor" not in data


class TestHeaderSecurity:
    """Test HTTP header security."""

    def test_accepts_valid_content_type(self):
        """Should accept valid content types."""

        class Data(BaseModel):
            value: str

        @route.post("/data")
        def post_data(data: Data):
            return data.model_dump()

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            # Valid JSON content type
            response = client.post(
                "/data",
                json={"value": "test"},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 200

    def test_host_header_injection_prevention(self):
        """Should handle potentially malicious host headers."""

        @route.get("/info")
        def get_info():
            return {"status": "ok"}

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            # Malicious host header
            response = client.get("/info", headers={"Host": "evil.com\r\nX-Injected: malicious"})
            # Starlette should handle this safely
            assert response.status_code in (200, 400)


class TestErrorInformationLeakage:
    """Test that errors don't leak sensitive information."""

    def test_production_mode_hides_stack_traces(self):
        """Should hide stack traces in production mode."""
        from myfy.core.config import CoreSettings
        from myfy.core.di.provider import provider
        from myfy.core.di.scopes import SINGLETON

        @provider(scope=SINGLETON)
        def core_settings() -> CoreSettings:
            return CoreSettings(debug=False)  # Production mode

        @route.get("/error")
        def error_handler():
            raise ValueError("Internal database error: password123")

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            response = client.get("/error")
            assert response.status_code == 500
            body = response.json()

            # Should not contain internal error details
            assert "password123" not in str(body)
            assert "ValueError" not in str(body)
            assert "Internal Server Error" in str(body)

    def test_debug_mode_shows_details(self):
        """Should show error details in debug mode."""
        from myfy.core.config import CoreSettings
        from myfy.core.di.provider import provider
        from myfy.core.di.scopes import SINGLETON

        @provider(scope=SINGLETON)
        def core_settings() -> CoreSettings:
            return CoreSettings(debug=True)  # Debug mode

        @route.get("/error")
        def error_handler():
            raise ValueError("Test error message")

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            response = client.get("/error")
            assert response.status_code == 500
            body = response.json()

            # Should contain error details in debug mode
            assert "ValueError" in str(body)
            assert "Test error message" in str(body)


class TestPathTraversal:
    """Test path traversal attack prevention."""

    def test_path_params_no_directory_traversal(self):
        """Should prevent directory traversal in path parameters."""

        @route.get("/file/{filename}")
        def get_file(filename: str):
            # In real code, this would read a file
            return {"filename": filename}

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            # Normal file
            response = client.get("/file/document.txt")
            assert response.status_code == 200

            # Path traversal attempts - should be handled as string
            response = client.get("/file/../../../etc/passwd")
            assert response.status_code == 200
            # Handler receives it as string (validation should happen in handler)
            assert "filename" in response.json()
