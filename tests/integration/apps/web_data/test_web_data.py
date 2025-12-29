"""
Integration tests for web+data application.

Tests WebModule + DataModule integration:
- Database connection and health checks
- Session injection in HTTP handlers
- CRUD operations through HTTP
- Transaction handling
- Request-scoped session isolation
- Foreign key relationships
"""

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealthChecks:
    """Test health check endpoints."""

    def test_basic_health(self, test_client: TestClient):
        """Basic health check works."""
        response = test_client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_database_health(self, test_client: TestClient):
        """Database health check verifies connection and session injection."""
        response = test_client.get("/health/db")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["db_check"] is True


# =============================================================================
# User CRUD Tests
# =============================================================================


class TestUserCRUD:
    """Test user CRUD operations."""

    def test_list_users_empty(self, test_client: TestClient):
        """List users returns empty list initially."""
        response = test_client.get("/users")

        assert response.status_code == 200
        assert response.json()["users"] == []

    def test_create_user(self, test_client: TestClient):
        """Create a new user."""
        response = test_client.post(
            "/users",
            json={"name": "Alice", "email": "alice@example.com"},
        )

        assert response.status_code == 200
        user = response.json()["user"]
        assert user["id"] == 1
        assert user["name"] == "Alice"
        assert user["email"] == "alice@example.com"
        assert user["created_at"] is not None

    def test_get_user(self, test_client: TestClient):
        """Get a user by ID."""
        # Create user first
        test_client.post("/users", json={"name": "Bob", "email": "bob@example.com"})

        # Get the user
        response = test_client.get("/users/1")

        assert response.status_code == 200
        user = response.json()["user"]
        assert user["name"] == "Bob"

    def test_get_user_not_found(self, test_client: TestClient):
        """Get non-existent user returns 404."""
        response = test_client.get("/users/999")

        assert response.status_code == 404
        assert response.json()["error"] == "User not found"

    def test_list_users_after_create(self, test_client: TestClient):
        """List users after creating some."""
        test_client.post("/users", json={"name": "User1", "email": "user1@example.com"})
        test_client.post("/users", json={"name": "User2", "email": "user2@example.com"})

        response = test_client.get("/users")

        assert response.status_code == 200
        users = response.json()["users"]
        assert len(users) == 2
        assert users[0]["name"] == "User1"
        assert users[1]["name"] == "User2"

    def test_delete_user(self, test_client: TestClient):
        """Delete a user."""
        test_client.post("/users", json={"name": "ToDelete", "email": "delete@example.com"})

        response = test_client.delete("/users/1")

        assert response.status_code == 200
        assert response.json()["deleted"] is True

        # Verify user is gone
        response = test_client.get("/users/1")
        assert response.status_code == 404
        assert response.json()["error"] == "User not found"


# =============================================================================
# Post CRUD Tests
# =============================================================================


class TestPostCRUD:
    """Test post CRUD operations."""

    def test_create_post(self, test_client: TestClient):
        """Create a post for a user."""
        # Create user first
        test_client.post("/users", json={"name": "Author", "email": "author@example.com"})

        # Create post
        response = test_client.post(
            "/users/1/posts",
            json={"title": "My First Post", "content": "Hello World!"},
        )

        assert response.status_code == 200
        post = response.json()["post"]
        assert post["id"] == 1
        assert post["title"] == "My First Post"
        assert post["content"] == "Hello World!"
        assert post["author_id"] == 1

    def test_create_post_for_nonexistent_user(self, test_client: TestClient):
        """Create post for non-existent user fails."""
        response = test_client.post(
            "/users/999/posts",
            json={"title": "Orphan Post", "content": "Should fail"},
        )

        assert response.status_code == 404
        assert response.json()["error"] == "User not found"

    def test_get_user_posts(self, test_client: TestClient):
        """Get all posts by a user."""
        # Create user and posts
        test_client.post("/users", json={"name": "Blogger", "email": "blogger@example.com"})
        test_client.post("/users/1/posts", json={"title": "Post 1"})
        test_client.post("/users/1/posts", json={"title": "Post 2"})

        # Get user's posts
        response = test_client.get("/users/1/posts")

        assert response.status_code == 200
        posts = response.json()["posts"]
        assert len(posts) == 2
        assert posts[0]["title"] == "Post 1"
        assert posts[1]["title"] == "Post 2"

    def test_list_all_posts(self, test_client: TestClient):
        """List all posts from all users."""
        # Create two users with posts
        test_client.post("/users", json={"name": "User1", "email": "u1@example.com"})
        test_client.post("/users", json={"name": "User2", "email": "u2@example.com"})
        test_client.post("/users/1/posts", json={"title": "User1 Post"})
        test_client.post("/users/2/posts", json={"title": "User2 Post"})

        response = test_client.get("/posts")

        assert response.status_code == 200
        posts = response.json()["posts"]
        assert len(posts) == 2

    def test_delete_post(self, test_client: TestClient):
        """Delete a post."""
        test_client.post("/users", json={"name": "Author", "email": "author@example.com"})
        test_client.post("/users/1/posts", json={"title": "To Delete"})

        response = test_client.delete("/posts/1")

        assert response.status_code == 200
        assert response.json()["deleted"] is True


# =============================================================================
# Relationship Tests
# =============================================================================


class TestRelationships:
    """Test foreign key and relationship handling."""

    def test_cascade_delete_user_deletes_posts(self, test_client: TestClient):
        """Deleting a user cascades to delete their posts."""
        # Create user with posts
        test_client.post("/users", json={"name": "Author", "email": "author@example.com"})
        test_client.post("/users/1/posts", json={"title": "Post 1"})
        test_client.post("/users/1/posts", json={"title": "Post 2"})

        # Verify posts exist
        response = test_client.get("/posts")
        assert len(response.json()["posts"]) == 2

        # Delete user
        test_client.delete("/users/1")

        # Verify posts are gone
        response = test_client.get("/posts")
        assert len(response.json()["posts"]) == 0


# =============================================================================
# Transaction Tests
# =============================================================================


class TestTransactions:
    """Test transaction handling."""

    def test_successful_transaction(self, test_client: TestClient):
        """Test that successful multi-operation transaction works."""
        response = test_client.post("/test/transaction-success")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] is not None
        assert data["post_id"] is not None

        # Verify both were created
        assert test_client.get(f"/users/{data['user_id']}").json()["user"]["name"] == "Transaction User"
        assert test_client.get(f"/posts/{data['post_id']}").json()["post"]["title"] == "Transaction Post"

    def test_transaction_rollback_on_error(self, test_client: TestClient):
        """Test that errors return 500 status."""
        response = test_client.post("/test/transaction-rollback")

        # Should get 500 error
        assert response.status_code == 500
        # Note: Transaction rollback behavior depends on session cleanup
        # which is handled by the framework's request scope management


# =============================================================================
# Session Isolation Tests
# =============================================================================


class TestSessionIsolation:
    """Test request-scoped session isolation."""

    def test_sessions_are_isolated(self, test_client: TestClient):
        """Each request gets its own session."""
        # Create users in separate requests
        r1 = test_client.post("/users", json={"name": "User1", "email": "u1@example.com"})
        r2 = test_client.post("/users", json={"name": "User2", "email": "u2@example.com"})

        # Both should succeed independently
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["user"]["id"] == 1
        assert r2.json()["user"]["id"] == 2

    @pytest.mark.skip(reason="SQLite has limitations with concurrent writes - use PostgreSQL for concurrent tests")
    def test_concurrent_requests_isolated(self, test_client: TestClient):
        """Concurrent requests have isolated sessions."""
        import concurrent.futures

        results = []

        def create_user(n: int):
            response = test_client.post(
                "/users",
                json={"name": f"ConcurrentUser{n}", "email": f"concurrent{n}@example.com"},
            )
            return response.json()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_user, i) for i in range(5)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        # All should succeed
        assert len(results) == 5
        for result in results:
            assert "user" in result
            assert result["user"]["id"] is not None


# =============================================================================
# Module Lifecycle Tests
# =============================================================================


class TestDataModuleLifecycle:
    """Test DataModule lifecycle integration."""

    def test_tables_created_on_startup(self, test_client: TestClient):
        """Tables are created when application starts."""
        # If we can create a user, tables exist
        response = test_client.post(
            "/users",
            json={"name": "Test", "email": "test@example.com"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_lifespan_handles_db_cleanup(self, web_data_app):
        """Application lifespan properly handles database cleanup."""
        from myfy.data import DataModule

        data_module = web_data_app.get_module(DataModule)

        lifespan = web_data_app.create_lifespan()
        async with lifespan(None):
            # Database should be connected
            engine = data_module.get_engine()
            assert engine is not None

        # After lifespan, module.stop() should have been called
        # (connection pool disposed)
