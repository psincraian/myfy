"""
Full stack example application.

A complete application using all modules: WebModule + DataModule + FrontendModule.

This represents a realistic todo application that:
- Stores tasks in a database (DataModule)
- Exposes REST API endpoints (WebModule)
- Renders HTML pages with templates (FrontendModule)
"""

from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.templating import Jinja2Templates

from myfy.core import Application
from myfy.core.config import BaseSettings
from myfy.data import DataModule, DatabaseSettings
from myfy.frontend import FrontendModule
from myfy.frontend.config import FrontendSettings
from myfy.web import WebModule
from myfy.web.routing import Router

from .models import Base, Task


# =============================================================================
# Settings
# =============================================================================


class FullStackSettings(BaseSettings):
    """Settings for full stack test application."""

    app_name: str = "Full Stack Todo App"
    debug: bool = True

    model_config = {"env_prefix": "FULL_STACK_TEST_"}


# =============================================================================
# Request Models
# =============================================================================


class CreateTaskRequest(BaseModel):
    """Request body for creating a task."""

    title: str
    description: str | None = None


class UpdateTaskRequest(BaseModel):
    """Request body for updating a task."""

    title: str | None = None
    description: str | None = None
    status: str | None = None


# =============================================================================
# Template Setup
# =============================================================================


def setup_templates(templates_dir: Path, static_dir: Path):
    """Create templates for the full stack app."""
    templates_dir.mkdir(parents=True, exist_ok=True)
    static_dir.mkdir(parents=True, exist_ok=True)

    # Base template
    (templates_dir / "base.html").write_text(
        """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ app_name }}{% endblock %}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <nav>
        <a href="/">Home</a>
        <a href="/tasks">Tasks</a>
    </nav>
    <main>
        {% block content %}{% endblock %}
    </main>
</body>
</html>"""
    )

    # Index page
    (templates_dir / "index.html").write_text(
        """{% extends "base.html" %}

{% block title %}Home - {{ app_name }}{% endblock %}

{% block content %}
<h1>Welcome to {{ app_name }}</h1>
<p>A full-stack todo application built with myfy.</p>
<p><a href="/tasks">View Tasks ({{ task_count }} total)</a></p>
{% endblock %}"""
    )

    # Create tasks subdirectory first
    (templates_dir / "tasks").mkdir(exist_ok=True)

    # Task list page
    (templates_dir / "tasks" / "list.html").write_text(
        """{% extends "base.html" %}

{% block title %}Tasks - {{ app_name }}{% endblock %}

{% block content %}
<h1>Tasks</h1>

<section class="task-list">
    {% if tasks %}
    <ul>
        {% for task in tasks %}
        <li class="task task-{{ task.status }}">
            <strong>{{ task.title }}</strong>
            {% if task.description %}
            <p>{{ task.description }}</p>
            {% endif %}
            <span class="status">{{ task.status }}</span>
            <a href="/tasks/{{ task.id }}">View</a>
        </li>
        {% endfor %}
    </ul>
    {% else %}
    <p class="empty">No tasks yet. Create one via the API!</p>
    {% endif %}
</section>

<section class="summary">
    <p>Total: {{ tasks | length }} tasks</p>
    <p>Pending: {{ tasks | selectattr('status', 'equalto', 'pending') | list | length }}</p>
    <p>Completed: {{ tasks | selectattr('status', 'equalto', 'completed') | list | length }}</p>
</section>
{% endblock %}"""
    )

    # Task detail page
    (templates_dir / "tasks" / "detail.html").write_text(
        """{% extends "base.html" %}

{% block title %}{{ task.title }} - {{ app_name }}{% endblock %}

{% block content %}
<article class="task-detail">
    <h1>{{ task.title }}</h1>
    <p class="status">Status: {{ task.status }}</p>
    {% if task.description %}
    <div class="description">
        <h2>Description</h2>
        <p>{{ task.description }}</p>
    </div>
    {% endif %}
    <a href="/tasks">Back to list</a>
</article>
{% endblock %}"""
    )

    # Error page
    (templates_dir / "error.html").write_text(
        """{% extends "base.html" %}

{% block title %}Error - {{ app_name }}{% endblock %}

{% block content %}
<h1>Error</h1>
<p>{{ error_message }}</p>
<a href="/">Go Home</a>
{% endblock %}"""
    )

    # Static files
    dist_dir = static_dir / "dist"
    dist_dir.mkdir(exist_ok=True)

    (dist_dir / "style.css").write_text(
        """* { box-sizing: border-box; }
body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
nav { margin-bottom: 20px; }
nav a { margin-right: 10px; }
.task { padding: 10px; margin: 5px 0; border: 1px solid #ccc; border-radius: 4px; }
.task-pending { border-left: 4px solid orange; }
.task-completed { border-left: 4px solid green; }
.status { font-size: 0.9em; color: #666; }
.empty { color: #666; font-style: italic; }
.summary { margin-top: 20px; padding: 10px; background: #f5f5f5; border-radius: 4px; }"""
    )


# =============================================================================
# Application Factory
# =============================================================================


def create_app(
    base_path: Path,
    database_url: str = "sqlite+aiosqlite:///:memory:",
) -> tuple[Application, Router]:
    """
    Create the full stack test application.

    Args:
        base_path: Base path for templates and static files
        database_url: Database URL

    Returns:
        Tuple of (Application, Router)
    """
    templates_dir = base_path / "templates"
    static_dir = base_path / "static"

    # Setup templates
    setup_templates(templates_dir, static_dir)

    router = Router()

    # =============================================================================
    # API Routes (JSON)
    # =============================================================================

    @router.get("/api/health")
    async def api_health(session: AsyncSession):
        """API health check with database connection."""
        await session.execute(select(1))
        return {"status": "ok", "database": "connected"}

    @router.get("/api/tasks")
    async def api_list_tasks(session: AsyncSession):
        """API: List all tasks."""
        result = await session.execute(select(Task).order_by(Task.id))
        tasks = result.scalars().all()
        return {"tasks": [t.to_dict() for t in tasks]}

    @router.post("/api/tasks")
    async def api_create_task(data: CreateTaskRequest, session: AsyncSession):
        """API: Create a new task."""
        task = Task(title=data.title, description=data.description)
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return {"task": task.to_dict()}

    @router.get("/api/tasks/{task_id}")
    async def api_get_task(task_id: int, session: AsyncSession):
        """API: Get a task by ID."""
        task = await session.get(Task, task_id)
        if task is None:
            return JSONResponse({"error": "Task not found"}, status_code=404)
        return {"task": task.to_dict()}

    @router.patch("/api/tasks/{task_id}")
    async def api_update_task(task_id: int, data: UpdateTaskRequest, session: AsyncSession):
        """API: Update a task."""
        task = await session.get(Task, task_id)
        if task is None:
            return JSONResponse({"error": "Task not found"}, status_code=404)

        if data.title is not None:
            task.title = data.title
        if data.description is not None:
            task.description = data.description
        if data.status is not None:
            task.status = data.status

        await session.commit()
        await session.refresh(task)
        return {"task": task.to_dict()}

    @router.delete("/api/tasks/{task_id}")
    async def api_delete_task(task_id: int, session: AsyncSession):
        """API: Delete a task."""
        task = await session.get(Task, task_id)
        if task is None:
            return JSONResponse({"error": "Task not found"}, status_code=404)
        await session.delete(task)
        await session.commit()
        return {"deleted": True}

    # =============================================================================
    # Web Routes (HTML)
    # =============================================================================

    @router.get("/")
    async def index(
        request: Request,
        templates: Jinja2Templates,
        settings: FullStackSettings,
        session: AsyncSession,
    ) -> HTMLResponse:
        """Home page showing task count from database."""
        result = await session.execute(select(Task))
        task_count = len(result.scalars().all())

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "app_name": settings.app_name,
                "task_count": task_count,
            },
        )

    @router.get("/tasks")
    async def task_list(
        request: Request,
        templates: Jinja2Templates,
        settings: FullStackSettings,
        session: AsyncSession,
    ) -> HTMLResponse:
        """Task list page."""
        result = await session.execute(select(Task).order_by(Task.id))
        tasks = result.scalars().all()

        return templates.TemplateResponse(
            request=request,
            name="tasks/list.html",
            context={
                "app_name": settings.app_name,
                "tasks": [t.to_dict() for t in tasks],
            },
        )

    @router.get("/tasks/{task_id}")
    async def task_detail(
        request: Request,
        task_id: int,
        templates: Jinja2Templates,
        settings: FullStackSettings,
        session: AsyncSession,
    ) -> HTMLResponse:
        """Task detail page."""
        task = await session.get(Task, task_id)
        if task is None:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "app_name": settings.app_name,
                    "error_message": "Task not found",
                },
                status_code=404,
            )

        return templates.TemplateResponse(
            request=request,
            name="tasks/detail.html",
            context={
                "app_name": settings.app_name,
                "task": task.to_dict(),
            },
        )

    # =============================================================================
    # Create Application with All Modules
    # =============================================================================

    db_settings = DatabaseSettings(
        database_url=database_url,
        echo=False,
        environment="test",
    )

    app = Application(settings_class=FullStackSettings, auto_discover=False)

    # Add modules in dependency order (framework handles this, but being explicit)
    app.add_module(WebModule(router=router))
    app.add_module(
        DataModule(
            settings=db_settings,
            auto_create_tables=True,
            metadata=Base.metadata,
        )
    )
    app.add_module(
        FrontendModule(
            templates_dir=str(templates_dir),
            static_dir=str(static_dir),
            auto_init=False,
        )
    )

    return app, router
