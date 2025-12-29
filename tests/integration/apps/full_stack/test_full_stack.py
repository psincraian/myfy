"""
Integration tests for full stack application.

Tests all modules working together: WebModule + DataModule + FrontendModule.

This verifies:
- Module initialization order and dependency resolution
- Cross-module service injection (DB session + Templates in same handler)
- API endpoints with database operations
- HTML pages with data from database
- Complete application lifecycle
"""

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


# =============================================================================
# API Health Tests
# =============================================================================


class TestAPIHealth:
    """Test API health endpoints."""

    def test_api_health_with_database(self, test_client: TestClient):
        """API health check verifies database connection."""
        response = test_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"


# =============================================================================
# API CRUD Tests
# =============================================================================


class TestAPICRUD:
    """Test REST API CRUD operations."""

    def test_list_tasks_empty(self, test_client: TestClient):
        """List tasks returns empty initially."""
        response = test_client.get("/api/tasks")

        assert response.status_code == 200
        assert response.json()["tasks"] == []

    def test_create_task(self, test_client: TestClient):
        """Create a task via API."""
        response = test_client.post(
            "/api/tasks",
            json={"title": "Test Task", "description": "A test task"},
        )

        assert response.status_code == 200
        task = response.json()["task"]
        assert task["id"] == 1
        assert task["title"] == "Test Task"
        assert task["description"] == "A test task"
        assert task["status"] == "pending"

    def test_get_task(self, test_client: TestClient):
        """Get a task by ID."""
        # Create first
        test_client.post("/api/tasks", json={"title": "Get Me"})

        response = test_client.get("/api/tasks/1")

        assert response.status_code == 200
        assert response.json()["task"]["title"] == "Get Me"

    def test_update_task(self, test_client: TestClient):
        """Update a task via PATCH."""
        test_client.post("/api/tasks", json={"title": "Original"})

        response = test_client.patch(
            "/api/tasks/1",
            json={"title": "Updated", "status": "completed"},
        )

        assert response.status_code == 200
        task = response.json()["task"]
        assert task["title"] == "Updated"
        assert task["status"] == "completed"

    def test_delete_task(self, test_client: TestClient):
        """Delete a task."""
        test_client.post("/api/tasks", json={"title": "To Delete"})

        response = test_client.delete("/api/tasks/1")

        assert response.status_code == 200
        assert response.json()["deleted"] is True

        # Verify gone
        response = test_client.get("/api/tasks/1")
        assert response.status_code == 404
        assert response.json()["error"] == "Task not found"


# =============================================================================
# HTML Page Tests
# =============================================================================


class TestHTMLPages:
    """Test HTML page rendering with database data."""

    def test_home_page_renders(self, test_client: TestClient):
        """Home page renders with task count."""
        response = test_client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Full Stack Todo App" in response.text

    def test_home_page_shows_task_count(self, test_client: TestClient):
        """Home page shows correct task count from database."""
        # Create some tasks
        test_client.post("/api/tasks", json={"title": "Task 1"})
        test_client.post("/api/tasks", json={"title": "Task 2"})
        test_client.post("/api/tasks", json={"title": "Task 3"})

        response = test_client.get("/")

        assert response.status_code == 200
        assert "3 total" in response.text

    def test_task_list_page_shows_tasks(self, test_client: TestClient):
        """Task list page shows tasks from database."""
        test_client.post("/api/tasks", json={"title": "Buy groceries"})
        test_client.post("/api/tasks", json={"title": "Write code"})

        response = test_client.get("/tasks")

        assert response.status_code == 200
        assert "Buy groceries" in response.text
        assert "Write code" in response.text

    def test_task_list_page_shows_status(self, test_client: TestClient):
        """Task list page shows task status."""
        test_client.post("/api/tasks", json={"title": "Pending Task"})
        test_client.patch("/api/tasks/1", json={"status": "completed"})
        test_client.post("/api/tasks", json={"title": "Another Task"})

        response = test_client.get("/tasks")

        assert response.status_code == 200
        # Check status indicators
        assert "completed" in response.text
        assert "pending" in response.text

    def test_task_detail_page(self, test_client: TestClient):
        """Task detail page shows task details."""
        test_client.post(
            "/api/tasks",
            json={"title": "Important Task", "description": "Do this carefully"},
        )

        response = test_client.get("/tasks/1")

        assert response.status_code == 200
        assert "Important Task" in response.text
        assert "Do this carefully" in response.text

    def test_task_detail_not_found(self, test_client: TestClient):
        """Task detail page shows error for non-existent task."""
        response = test_client.get("/tasks/999")

        assert response.status_code == 404
        assert "Task not found" in response.text


# =============================================================================
# Cross-Module Integration Tests
# =============================================================================


class TestCrossModuleIntegration:
    """Test that all modules work together correctly."""

    def test_api_and_html_see_same_data(self, test_client: TestClient):
        """API and HTML endpoints see the same database data."""
        # Create via API
        test_client.post("/api/tasks", json={"title": "Cross Module Task"})

        # Read via API
        api_response = test_client.get("/api/tasks")
        assert len(api_response.json()["tasks"]) == 1

        # Read via HTML
        html_response = test_client.get("/tasks")
        assert "Cross Module Task" in html_response.text

    def test_html_and_api_work_together(self, test_client: TestClient):
        """HTML pages and API endpoints both work in same app."""
        # Get HTML page (uses DB + templates)
        html_response = test_client.get("/tasks")
        assert html_response.status_code == 200
        assert "text/html" in html_response.headers["content-type"]

        # Get API response
        api_response = test_client.get("/api/tasks")
        assert api_response.status_code == 200
        assert "application/json" in api_response.headers["content-type"]

    def test_templates_and_session_in_same_handler(self, test_client: TestClient):
        """Handler can inject both Jinja2Templates and AsyncSession."""
        # Create task
        test_client.post("/api/tasks", json={"title": "DI Test"})

        # The detail page handler injects both templates and session
        response = test_client.get("/tasks/1")

        # If both were injected correctly, page renders with DB data
        assert response.status_code == 200
        assert "DI Test" in response.text


# =============================================================================
# Module Initialization Tests
# =============================================================================


class TestModuleInitialization:
    """Test correct module initialization order."""

    def test_all_modules_initialized(self, full_stack_app):
        """All three modules are initialized."""
        from myfy.data import DataModule
        from myfy.frontend import FrontendModule
        from myfy.web import WebModule

        assert full_stack_app.has_module(WebModule)
        assert full_stack_app.has_module(DataModule)
        assert full_stack_app.has_module(FrontendModule)

    def test_modules_in_dependency_order(self, full_stack_app):
        """Modules are ordered by dependencies."""
        from myfy.frontend import FrontendModule
        from myfy.web import WebModule

        modules = full_stack_app._modules
        module_types = [type(m) for m in modules]

        # WebModule must come before FrontendModule
        web_idx = module_types.index(WebModule)
        frontend_idx = module_types.index(FrontendModule)
        assert web_idx < frontend_idx


# =============================================================================
# Lifecycle Tests
# =============================================================================


class TestFullStackLifecycle:
    """Test complete application lifecycle."""

    @pytest.mark.asyncio
    async def test_lifespan_starts_all_modules(self, full_stack_app):
        """Lifespan properly starts all modules."""
        lifespan = full_stack_app.create_lifespan()

        async with lifespan(None):
            # All modules should be running
            # DataModule should have engine
            from myfy.data import DataModule

            data_module = full_stack_app.get_module(DataModule)
            assert data_module.get_engine() is not None

    @pytest.mark.asyncio
    async def test_lifespan_stops_all_modules(self, full_stack_app):
        """Lifespan properly stops all modules."""
        lifespan = full_stack_app.create_lifespan()

        async with lifespan(None):
            pass

        # After exiting lifespan, cleanup should have happened


# =============================================================================
# Concurrent Request Tests
# =============================================================================


class TestConcurrentRequests:
    """Test concurrent requests with all modules."""

    def test_concurrent_api_and_html_requests(self, test_client: TestClient):
        """Concurrent API and HTML requests work correctly."""
        import concurrent.futures

        # Create some initial data
        for i in range(5):
            test_client.post("/api/tasks", json={"title": f"Task {i}"})

        results = []

        def make_api_request():
            return ("api", test_client.get("/api/tasks").json())

        def make_html_request():
            return ("html", test_client.get("/tasks").text)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for _ in range(5):
                futures.append(executor.submit(make_api_request))
                futures.append(executor.submit(make_html_request))

            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        # All requests should succeed
        assert len(results) == 10

        api_results = [r for r in results if r[0] == "api"]
        html_results = [r for r in results if r[0] == "html"]

        assert len(api_results) == 5
        assert len(html_results) == 5

        # All API results should have 5 tasks
        for _, data in api_results:
            assert len(data["tasks"]) == 5

        # All HTML results should contain task list
        for _, html in html_results:
            assert "Task 0" in html
