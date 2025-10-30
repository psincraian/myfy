# Tutorial: Build a Task API

Learn myfy by building a complete REST API for task management.

**What you'll build:**
- Task CRUD operations
- Type-safe configuration
- Dependency injection
- Request validation
- In-memory database

**Time:** 15-20 minutes

---

## Step 1: Project Setup

Create a new directory:

```bash
mkdir task-api
cd task-api
```

---

## Step 2: Define Your Models

Create `models.py`:

```python
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Task(BaseModel):
    id: int
    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO
    created_at: datetime = Field(default_factory=datetime.now)


class CreateTaskDTO(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None


class UpdateTaskDTO(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus | None = None
```

!!! tip "Why Pydantic?"
    Pydantic provides runtime validation and serialization out of the box. myfy embraces Pydantic throughout.

---

## Step 3: Create a Repository

Create `repository.py`:

```python
from models import Task, TaskStatus


class TaskRepository:
    """In-memory task storage."""

    def __init__(self):
        self._tasks: dict[int, Task] = {}
        self._next_id = 1

    def create(self, title: str, description: str | None = None) -> Task:
        task = Task(
            id=self._next_id,
            title=title,
            description=description,
            status=TaskStatus.TODO,
        )
        self._tasks[task.id] = task
        self._next_id += 1
        return task

    def get(self, task_id: int) -> Task | None:
        return self._tasks.get(task_id)

    def list_all(self) -> list[Task]:
        return list(self._tasks.values())

    def update(self, task_id: int, **updates) -> Task | None:
        task = self._tasks.get(task_id)
        if not task:
            return None

        # Update fields
        for field, value in updates.items():
            if value is not None and hasattr(task, field):
                setattr(task, field, value)

        return task

    def delete(self, task_id: int) -> bool:
        return self._tasks.pop(task_id, None) is not None
```

---

## Step 4: Configure Dependency Injection

Create `config.py`:

```python
from myfy.core import BaseSettings, provider, SINGLETON
from pydantic import Field
from repository import TaskRepository


class AppSettings(BaseSettings):
    app_name: str = Field(default="Task API")
    max_tasks: int = Field(default=1000)


@provider(scope=SINGLETON)
def task_repository() -> TaskRepository:
    """Provide task repository as singleton."""
    return TaskRepository()
```

!!! note "Singleton Scope"
    `SINGLETON` means one instance for the entire application. Perfect for repositories and databases.

---

## Step 5: Create HTTP Routes

Create `routes.py`:

```python
from myfy.web import route
from models import Task, CreateTaskDTO, UpdateTaskDTO
from repository import TaskRepository


@route.get("/tasks")
async def list_tasks(repo: TaskRepository) -> list[Task]:
    """List all tasks."""
    return repo.list_all()


@route.get("/tasks/{task_id}")
async def get_task(task_id: int, repo: TaskRepository) -> Task:
    """Get a single task by ID."""
    task = repo.get(task_id)
    if not task:
        from starlette.exceptions import HTTPException
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@route.post("/tasks", status_code=201)
async def create_task(body: CreateTaskDTO, repo: TaskRepository) -> Task:
    """Create a new task."""
    return repo.create(title=body.title, description=body.description)


@route.patch("/tasks/{task_id}")
async def update_task(
    task_id: int,
    body: UpdateTaskDTO,
    repo: TaskRepository,
) -> Task:
    """Update an existing task."""
    updates = body.model_dump(exclude_unset=True)
    task = repo.update(task_id, **updates)

    if not task:
        from starlette.exceptions import HTTPException
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@route.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int, repo: TaskRepository) -> None:
    """Delete a task."""
    if not repo.delete(task_id):
        from starlette.exceptions import HTTPException
        raise HTTPException(status_code=404, detail="Task not found")
```

!!! tip "Automatic DI"
    Notice how `repo: TaskRepository` is automatically injected? myfy resolves dependencies at compile-time.

---

## Step 6: Wire It All Together

Create `app.py`:

```python
from myfy.core import Application
from myfy.web import WebModule
from config import AppSettings


# Create application
app = Application(settings_class=AppSettings, auto_discover=False)
app.add_module(WebModule())


if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run())
```

---

## Step 7: Create Environment Config

Create `.env`:

```bash
APP_NAME=Task Management API
MAX_TASKS=100
```

---

## Step 8: Run Your API

```bash
uv run myfy run
```

You should see:

```
🚀 Starting myfy development server...
✓ Found application in app.py
📡 Listening on http://127.0.0.1:8000
📦 Loaded 2 module(s)
🔄 Reload enabled - watching for file changes
```

---

## Step 9: Test Your API

### Create a Task

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Learn myfy", "description": "Complete the tutorial"}'
```

Response:
```json
{
  "id": 1,
  "title": "Learn myfy",
  "description": "Complete the tutorial",
  "status": "todo",
  "created_at": "2025-10-26T10:30:00"
}
```

### List All Tasks

```bash
curl http://127.0.0.1:8000/tasks
```

### Get Single Task

```bash
curl http://127.0.0.1:8000/tasks/1
```

### Update Task

```bash
curl -X PATCH http://127.0.0.1:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

### Delete Task

```bash
curl -X DELETE http://127.0.0.1:8000/tasks/1
```

---

## Step 10: Explore CLI Tools

### List Routes

```bash
uv run myfy routes
```

Output:
```
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━┓
┃ Method ┃ Path            ┃ Handler      ┃ Name ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━┩
│ GET    │ /tasks          │ list_tasks   │ -    │
│ GET    │ /tasks/{id}     │ get_task     │ -    │
│ POST   │ /tasks          │ create_task  │ -    │
│ PATCH  │ /tasks/{id}     │ update_task  │ -    │
│ DELETE │ /tasks/{id}     │ delete_task  │ -    │
└────────┴─────────────────┴──────────────┴──────┘
```

### Check Application Health

```bash
uv run myfy doctor
```

---

## What You've Learned

✅ **Models with Pydantic** - Type-safe data structures
✅ **Dependency Injection** - Automatic service resolution
✅ **Repository Pattern** - Clean separation of concerns
✅ **HTTP Routes** - Decorator-based routing
✅ **Configuration** - Environment-based settings
✅ **CLI Tools** - Built-in development tools

---

## Next Steps

### Add a Frontend

Want to add a web UI? Initialize the frontend module:

```bash
# In your project directory
uv run myfy frontend init
```

This creates a styled homepage with Tailwind 4 and DaisyUI 5. Update your `app.py` to include the frontend module:

```python
from myfy.core import Application
from myfy.web import WebModule
from myfy.frontend import FrontendModule, render_template  # Add this
from config import AppSettings
from starlette.requests import Request  # Add this
from starlette.templating import Jinja2Templates  # Add this

# Create application
app = Application(settings_class=AppSettings, auto_discover=False)
app.add_module(WebModule())
app.add_module(FrontendModule())  # Add this line

# Add a frontend route
@route.get("/")
async def home(request: Request, templates: Jinja2Templates):
    return render_template(
        "home.html",
        request=request,
        templates=templates,
        title="Task Management"
    )
```

Now you have both an API (`/tasks`) and a web UI (`/`)!

**Learn more:** [Frontend Module Documentation](../modules/frontend.md)

### Add Database Support

Replace the in-memory repository with SQLAlchemy:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@provider(scope=SINGLETON)
async def database(settings: AppSettings):
    engine = create_async_engine(settings.database_url)
    return engine

@provider(scope=REQUEST)
async def session(db: Engine) -> AsyncSession:
    async with AsyncSession(db) as session:
        yield session
```

### Add Authentication

```python
@route.get("/tasks")
async def list_tasks(
    repo: TaskRepository,
    user: User = Depends(get_current_user)
) -> list[Task]:
    return repo.list_by_user(user.id)
```

### Add Testing

```python
import pytest
from myfy.core import Application

@pytest.fixture
def app():
    return Application(settings_class=TestSettings)

def test_create_task(app):
    repo = app.container.get(TaskRepository)
    task = repo.create("Test task")
    assert task.id == 1
    assert task.title == "Test task"
```

---

## Full Project Structure

```
task-api/
├── app.py           # Application entry point
├── config.py        # Settings and providers
├── models.py        # Pydantic models
├── repository.py    # Data access layer
├── routes.py        # HTTP handlers
└── .env             # Environment variables
```

---

## Compare with FastAPI

If you're coming from FastAPI, here's what's different:

| Feature | FastAPI | myfy |
|---------|---------|------|
| **DI Registration** | Inline `Depends()` | `@provider` decorator |
| **Scopes** | No built-in scopes | `SINGLETON`, `REQUEST`, `TASK` |
| **Config** | Manual setup | `BaseSettings` with profiles |
| **Modules** | No concept | First-class modules |
| **CLI** | No built-in CLI | `myfy run`, `myfy routes` |

---

## Troubleshooting

### Module Not Found

```bash
# Make sure all files are in the same directory
ls -la

# Should see:
# app.py, config.py, models.py, repository.py, routes.py
```

### Import Errors

```python
# In app.py, import your modules explicitly
import config  # This registers providers
import routes  # This registers routes
```

### Port in Use

```bash
uv run myfy run --port 8001
```

---

## Resources

- [Quick Reference](quick-reference.md) - Common patterns
- [Core Concepts: DI](../core-concepts/dependency-injection.md) - Deep dive
- [Testing Guide](../guides/testing.md) - Test your application
- [Deployment Guide](../guides/deployment.md) - Go to production
