"""
Integration tests for the full myfy stack.

Tests the complete integration of core, web, and DI systems.
"""

from pydantic import BaseModel
from starlette.testclient import TestClient

from myfy.core import Application
from myfy.core.di.provider import provider
from myfy.core.di.scopes import SINGLETON, Scope
from myfy.web import WebModule, route


class User(BaseModel):
    """Test user model."""

    id: int
    name: str
    email: str


class Database:
    """Mock database service."""

    def __init__(self):
        self.users = {
            1: User(id=1, name="Alice", email="alice@example.com"),
            2: User(id=2, name="Bob", email="bob@example.com"),
        }

    def get_user(self, user_id: int) -> User | None:
        return self.users.get(user_id)

    def create_user(self, user: User) -> User:
        self.users[user.id] = user
        return user

    def list_users(self) -> list[User]:
        return list(self.users.values())


class UserRepository:
    """User repository using database."""

    def __init__(self, db: Database):
        self.db = db

    def find_by_id(self, user_id: int) -> User | None:
        return self.db.get_user(user_id)

    def create(self, user: User) -> User:
        return self.db.create_user(user)

    def list_all(self) -> list[User]:
        return self.db.list_users()


class TestFullStackIntegration:
    """Test full stack integration with DI and web."""

    def test_end_to_end_request_with_di(self):
        """Should handle request with full DI injection."""

        # Setup providers
        @provider(scope=SINGLETON)
        def database() -> Database:
            return Database()

        @provider(scope=SINGLETON)
        def user_repository(db: Database) -> UserRepository:
            return UserRepository(db)

        # Setup routes
        @route.get("/users/{user_id}")
        def get_user(user_id: int, repo: UserRepository):
            user = repo.find_by_id(user_id)
            if user is None:
                return {"error": "User not found"}, 404
            return user.model_dump()

        @route.get("/users")
        def list_users(repo: UserRepository):
            users = repo.list_all()
            return [u.model_dump() for u in users]

        @route.post("/users")
        def create_user(user: User, repo: UserRepository):
            created = repo.create(user)
            return created.model_dump()

        # Create application
        app = Application(modules=[WebModule()])
        app.initialize()

        # Get ASGI app
        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        # Test requests
        with TestClient(asgi_app.app) as client:
            # Test GET single user
            response = client.get("/users/1")
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Alice"
            assert data["email"] == "alice@example.com"

            # Test GET all users
            response = client.get("/users")
            assert response.status_code == 200
            users = response.json()
            assert len(users) == 2

            # Test POST create user
            new_user = {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
            response = client.post("/users", json=new_user)
            assert response.status_code == 200
            created = response.json()
            assert created["name"] == "Charlie"

            # Verify user was created
            response = client.get("/users/3")
            assert response.status_code == 200
            assert response.json()["name"] == "Charlie"

    def test_request_scoped_dependencies(self):
        """Should create new instances for request-scoped dependencies."""
        request_count = {"count": 0}

        @provider(scope=Scope.REQUEST)
        def request_service() -> dict:
            request_count["count"] += 1
            return {"request_id": request_count["count"]}

        @route.get("/test")
        def test_handler(svc: dict):
            return svc

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            # First request
            response1 = client.get("/test")
            assert response1.json()["request_id"] == 1

            # Second request should get new instance
            response2 = client.get("/test")
            assert response2.json()["request_id"] == 2

    def test_error_handling(self):
        """Should handle errors properly."""

        @route.get("/error")
        def error_handler():
            raise ValueError("Test error")

        @route.get("/http-error")
        def http_error_handler():
            from starlette.exceptions import HTTPException

            raise HTTPException(status_code=400, detail="Bad request")

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            # HTTP exception should return proper status
            response = client.get("/http-error")
            assert response.status_code == 400
            assert "Bad request" in response.json()["detail"]

            # Server error should return 500
            response = client.get("/error")
            assert response.status_code == 500

    def test_multiple_modules(self):
        """Should work with multiple modules."""

        class ServiceA:
            def get_value(self):
                return "A"

        class ServiceB:
            def __init__(self, service_a: ServiceA):
                self.service_a = service_a

            def get_combined(self):
                return f"{self.service_a.get_value()}B"

        @provider()
        def service_a() -> ServiceA:
            return ServiceA()

        @provider()
        def service_b(a: ServiceA) -> ServiceB:
            return ServiceB(a)

        @route.get("/combined")
        def get_combined(b: ServiceB):
            return {"value": b.get_combined()}

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            response = client.get("/combined")
            assert response.status_code == 200
            assert response.json()["value"] == "AB"


class TestAsyncHandlers:
    """Test async handler support."""

    def test_async_handlers(self):
        """Should support async handlers."""

        @provider(scope=SINGLETON)
        def database() -> Database:
            return Database()

        @route.get("/async-users/{user_id}")
        async def get_user_async(user_id: int, db: Database):
            # Simulate async operation
            user = db.get_user(user_id)
            if user is None:
                return {"error": "Not found"}, 404
            return user.model_dump()

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            response = client.get("/async-users/1")
            assert response.status_code == 200
            assert response.json()["name"] == "Alice"

    def test_mixed_sync_async_handlers(self):
        """Should support mixed sync and async handlers."""

        @route.get("/sync")
        def sync_handler():
            return {"type": "sync"}

        @route.get("/async")
        async def async_handler():
            return {"type": "async"}

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            response = client.get("/sync")
            assert response.json()["type"] == "sync"

            response = client.get("/async")
            assert response.json()["type"] == "async"


class TestValidation:
    """Test request validation."""

    def test_path_param_validation(self):
        """Should validate path parameters."""

        @route.get("/items/{item_id}")
        def get_item(item_id: int):
            return {"item_id": item_id}

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            # Valid int
            response = client.get("/items/123")
            assert response.status_code == 200
            assert response.json()["item_id"] == 123

            # Invalid int should return 400
            response = client.get("/items/abc")
            assert response.status_code == 400

    def test_body_validation(self):
        """Should validate request body."""

        @route.post("/validate-user")
        def validate_user(user: User):
            return user.model_dump()

        app = Application(modules=[WebModule()])
        app.initialize()

        web_module = app.get_module("web")
        lifespan = app.create_lifespan()
        asgi_app = web_module.get_asgi_app(app.container, lifespan=lifespan)

        with TestClient(asgi_app.app) as client:
            # Valid body
            response = client.post(
                "/validate-user", json={"id": 1, "name": "Test", "email": "test@example.com"}
            )
            assert response.status_code == 200

            # Invalid body (missing required field)
            response = client.post("/validate-user", json={"id": 1, "name": "Test"})
            assert response.status_code == 422


class TestLifecycle:
    """Test application lifecycle."""

    def test_module_lifecycle_integration(self):
        """Should properly initialize and clean up modules."""
        lifecycle_events = []

        from myfy.core.module import IModule

        class TestModule(IModule):
            @property
            def name(self) -> str:
                return "test"

            def configure(self, app):
                lifecycle_events.append("configure")

            def compile(self, app):
                lifecycle_events.append("compile")

            async def start(self):
                lifecycle_events.append("start")

            async def stop(self):
                lifecycle_events.append("stop")

        app = Application(modules=[TestModule(), WebModule()])
        app.initialize()

        # Should have called configure and compile
        assert "configure" in lifecycle_events
        assert "compile" in lifecycle_events

        # Clean up
        lifecycle_events.clear()
