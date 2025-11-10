"""
Tests for request context management.

Tests request-scoped context and context variables.
"""

import pytest
from starlette.requests import Request
from starlette.testclient import TestClient

from myfy.web.context import (
    RequestContext,
    clear_request_context,
    get_request_context,
    set_request_context,
)


def create_test_request(method: str = "GET", path: str = "/test", headers: dict | None = None):
    """Helper to create test request."""
    from starlette.applications import Starlette

    app = Starlette()
    client = TestClient(app)

    header_list = []
    if headers:
        header_list = [(k.encode(), v.encode()) for k, v in headers.items()]

    return Request({"type": "http", "method": method, "path": path, "headers": header_list}, client)


class TestRequestContext:
    """Test RequestContext functionality."""

    def test_create_request_context(self):
        """Should create request context from request."""
        request = create_test_request()
        ctx = RequestContext(request)

        assert ctx.request is request
        assert isinstance(ctx._data, dict)

    def test_get_set_context_data(self):
        """Should get and set custom data."""
        request = create_test_request()
        ctx = RequestContext(request)

        ctx.set("user_id", 123)
        assert ctx.get("user_id") == 123

    def test_get_context_data_with_default(self):
        """Should return default for missing key."""
        request = create_test_request()
        ctx = RequestContext(request)

        assert ctx.get("missing", "default") == "default"

    def test_get_context_data_no_default(self):
        """Should return None for missing key without default."""
        request = create_test_request()
        ctx = RequestContext(request)

        assert ctx.get("missing") is None

    def test_method_property(self):
        """Should expose HTTP method."""
        request = create_test_request(method="POST")
        ctx = RequestContext(request)

        assert ctx.method == "POST"

    def test_url_property(self):
        """Should expose full URL."""
        request = create_test_request(path="/users/123")
        ctx = RequestContext(request)

        assert "/users/123" in ctx.url

    def test_path_property(self):
        """Should expose path."""
        request = create_test_request(path="/users/123")
        ctx = RequestContext(request)

        assert ctx.path == "/users/123"

    def test_headers_property(self):
        """Should expose headers as dict."""
        request = create_test_request(headers={"x-custom": "value"})
        ctx = RequestContext(request)

        headers = ctx.headers
        assert isinstance(headers, dict)
        assert headers.get("x-custom") == "value"

    @pytest.mark.asyncio
    async def test_json_method(self):
        """Should parse JSON body."""
        request = create_test_request(method="POST")
        request._body = b'{"name": "test"}'

        ctx = RequestContext(request)
        data = await ctx.json()

        assert data == {"name": "test"}

    @pytest.mark.asyncio
    async def test_body_method(self):
        """Should get raw body."""
        request = create_test_request(method="POST")
        request._body = b"raw content"

        ctx = RequestContext(request)
        body = await ctx.body()

        assert body == b"raw content"

    def test_repr(self):
        """Should have useful string representation."""
        request = create_test_request(method="GET", path="/users")
        ctx = RequestContext(request)

        repr_str = repr(ctx)
        assert "GET" in repr_str
        assert "/users" in repr_str


class TestContextVariables:
    """Test context variable management."""

    def test_set_and_get_request_context(self):
        """Should set and get request context."""
        request = create_test_request()
        ctx = RequestContext(request)

        set_request_context(ctx)
        retrieved = get_request_context()

        assert retrieved is ctx

    def test_get_request_context_when_not_set(self):
        """Should return None when context not set."""
        clear_request_context()
        ctx = get_request_context()

        assert ctx is None

    def test_clear_request_context(self):
        """Should clear request context."""
        request = create_test_request()
        ctx = RequestContext(request)

        set_request_context(ctx)
        clear_request_context()

        assert get_request_context() is None

    def test_context_isolation_between_calls(self):
        """Should isolate context between different calls."""
        request1 = create_test_request(path="/path1")
        ctx1 = RequestContext(request1)
        ctx1.set("id", 1)

        set_request_context(ctx1)
        assert get_request_context().get("id") == 1

        # Simulate new request
        clear_request_context()
        request2 = create_test_request(path="/path2")
        ctx2 = RequestContext(request2)
        ctx2.set("id", 2)

        set_request_context(ctx2)
        assert get_request_context().get("id") == 2

        # Previous context should not leak
        clear_request_context()
        assert get_request_context() is None


class TestRequestContextUsage:
    """Test typical usage patterns."""

    def test_context_for_storing_request_scoped_data(self):
        """Should store request-scoped data."""
        request = create_test_request()
        ctx = RequestContext(request)

        # Simulate middleware adding data
        ctx.set("request_id", "abc123")
        ctx.set("user", {"id": 1, "name": "John"})

        # Handler can retrieve it
        assert ctx.get("request_id") == "abc123"
        assert ctx.get("user")["id"] == 1

    def test_context_lifecycle(self):
        """Should follow request lifecycle."""
        # Before request
        assert get_request_context() is None

        # During request
        request = create_test_request()
        ctx = RequestContext(request)
        set_request_context(ctx)
        assert get_request_context() is not None

        # After request
        clear_request_context()
        assert get_request_context() is None

    @pytest.mark.asyncio
    async def test_context_with_multiple_data_items(self):
        """Should handle multiple data items."""
        request = create_test_request()
        ctx = RequestContext(request)

        # Store various types of data
        ctx.set("string", "value")
        ctx.set("int", 42)
        ctx.set("dict", {"key": "value"})
        ctx.set("list", [1, 2, 3])

        assert ctx.get("string") == "value"
        assert ctx.get("int") == 42
        assert ctx.get("dict") == {"key": "value"}
        assert ctx.get("list") == [1, 2, 3]
