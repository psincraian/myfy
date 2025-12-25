# Reference

Complete single-page reference for myfy framework. Use <kbd>Ctrl</kbd>+<kbd>F</kbd> to find what you need.

---

## Quick Start

### Minimal Application

```python
from myfy.core import Application
from myfy.web import route, WebModule

@route.get("/")
async def home() -> dict:
    return {"message": "Hello World"}

app = Application(auto_discover=False)
app.add_module(WebModule())
```

```bash
uv run myfy run
```

### Full-Stack with Frontend

```bash
uv run myfy frontend init
uv run myfy run
```

[:octicons-arrow-right-24: Installation Guide](getting-started/installation.md) · [:octicons-arrow-right-24: Tutorial](getting-started/tutorial.md)

---

## Dependency Injection

### Provider Scopes

| Scope | Lifetime | Use Case |
|-------|----------|----------|
| `SINGLETON` | Application | Database pools, caches, services |
| `REQUEST` | HTTP Request | Database sessions, request context |
| `TASK` | Background Task | Task-specific resources |

### Register Providers

```python
from myfy.core import provider, SINGLETON, REQUEST

@provider(scope=SINGLETON)
def database(settings: Settings) -> Database:
    return Database(settings.db_url)

@provider(scope=REQUEST)
def session(db: Database) -> Session:
    return db.create_session()
```

### Inject in Routes

```python
@route.get("/users")
async def list_users(db: Database, cache: Cache) -> list[User]:
    return await db.get_all_users()
```

[:octicons-arrow-right-24: DI Deep Dive](core-concepts/dependency-injection.md)

---

## Web Routes

### HTTP Methods

```python
from myfy.web import route

@route.get("/users")           # GET
@route.post("/users")          # POST
@route.put("/users/{id}")      # PUT
@route.patch("/users/{id}")    # PATCH
@route.delete("/users/{id}")   # DELETE
```

### Path Parameters

```python
@route.get("/users/{user_id}")
async def get_user(user_id: int) -> User:
    # user_id automatically converted to int
    return await service.get_user(user_id)

@route.get("/posts/{post_id}/comments/{comment_id}")
async def get_comment(post_id: int, comment_id: int) -> Comment:
    return await service.get_comment(post_id, comment_id)
```

### Query Parameters

Basic query parameters with defaults:

```python
@route.get("/users")
async def list_users(
    page: int = 1,
    limit: int = 10,
    sort: str = "name"
) -> list[User]:
    return await service.list_users(page, limit, sort)

# GET /users?page=2&limit=20&sort=created_at
```

**Query parameters with validation** (new in v0.1.2):

```python
from myfy.web import route, Query

@route.get("/search")
async def search(
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
) -> list[Result]:
    return await service.search(q, limit, page)
```

**Query constraints:**

| Constraint | Type | Description |
|------------|------|-------------|
| `ge` | int/float | Greater than or equal |
| `le` | int/float | Less than or equal |
| `gt` | int/float | Greater than |
| `lt` | int/float | Less than |
| `min_length` | int | Minimum string length |
| `max_length` | int | Maximum string length |
| `pattern` | str | Regex pattern |
| `alias` | str | Alternative query param name |

### Request Body

```python
from pydantic import BaseModel, Field

class CreateUserDTO(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    age: int = Field(ge=0, le=150)

@route.post("/users")
async def create_user(body: CreateUserDTO) -> User:
    return await service.create_user(body)
```

### Status Codes

```python
@route.post("/users", status_code=201)
async def create_user(body: CreateUserDTO) -> User:
    return await service.create_user(body)

@route.delete("/users/{id}", status_code=204)
async def delete_user(id: int) -> None:
    await service.delete_user(id)
```

### Response Types

```python
# Dict → JSON
@route.get("/user")
async def get_user() -> dict:
    return {"id": 1, "name": "John"}

# Pydantic model → JSON
@route.get("/user")
async def get_user() -> User:
    return User(id=1, name="John")

# Custom response
from starlette.responses import RedirectResponse

@route.get("/redirect")
async def redirect():
    return RedirectResponse(url="/home")
```

[:octicons-arrow-right-24: Web Module](modules/web.md)

---

## Error Handling

### WebError Hierarchy (new in v0.1.2)

All errors follow RFC 7807 Problem Details format:

```python
from myfy.web import errors

# Built-in errors
raise errors.NotFound("User not found")
raise errors.BadRequest("Invalid email format", field="email")
raise errors.Unauthorized("Invalid token")
raise errors.Forbidden("Access denied")
raise errors.Conflict("Username already taken")
raise errors.RateLimit("Too many requests", retry_after=60)
```

**Available errors:**

| Error | Status | Use Case |
|-------|--------|----------|
| `errors.BadRequest` | 400 | Invalid input, validation failures |
| `errors.Unauthorized` | 401 | Missing or invalid authentication |
| `errors.Forbidden` | 403 | Authenticated but not authorized |
| `errors.NotFound` | 404 | Resource doesn't exist |
| `errors.Conflict` | 409 | Duplicate entries, state conflicts |
| `errors.UnprocessableEntity` | 422 | Valid syntax, invalid semantics |
| `errors.RateLimit` | 429 | Too many requests |
| `errors.ServiceUnavailable` | 503 | Temporary outage |

### Custom Errors

```python
from myfy.web.exceptions import WebError

class PaymentRequiredError(WebError):
    status_code = 402
    error_type = "payment_required"

raise PaymentRequiredError("Insufficient credits", required=100)
```

### Response Format

Errors automatically return RFC 7807 Problem Details:

```json
{
    "type": "not_found",
    "title": "NotFoundError",
    "status": 404,
    "detail": "User not found",
    "user_id": 123
}
```

---

## Configuration

### Settings Class

```python
from myfy.core import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    app_name: str = Field(default="My App")
    debug: bool = Field(default=False)
    database_url: str
    api_key: str = Field(alias="API_KEY")
```

### Environment Files

```bash
# .env (default)
APP_NAME=My App
DATABASE_URL=postgresql://localhost/mydb

# .env.dev (MYFY_PROFILE=dev)
DEBUG=true
DATABASE_URL=postgresql://localhost/mydb_dev

# .env.prod (MYFY_PROFILE=prod)
DEBUG=false
DATABASE_URL=postgresql://prod-server/mydb
```

### Load Profile

```bash
MYFY_PROFILE=dev uv run myfy run
MYFY_PROFILE=prod uv run myfy run --no-reload
```

[:octicons-arrow-right-24: Configuration Guide](core-concepts/configuration.md)

---

## Modules

### Create Module

```python
from myfy.core import BaseModule, Container

class DataModule(BaseModule):
    def __init__(self):
        super().__init__("data")

    def configure(self, container: Container) -> None:
        container.register(Database, factory=create_db, scope=SINGLETON)

    async def start(self) -> None:
        self.db = await connect_database()

    async def stop(self) -> None:
        await self.db.disconnect()
```

### Register Module

```python
app = Application(auto_discover=False)
app.add_module(DataModule())
app.add_module(WebModule())
```

### Built-in Modules

| Module | Package | Purpose |
|--------|---------|---------|
| `WebModule` | myfy-web | HTTP/ASGI routing |
| `DataModule` | myfy-data | Async SQLAlchemy |
| `FrontendModule` | myfy-frontend | Tailwind, DaisyUI, Vite |

[:octicons-arrow-right-24: Modules Guide](core-concepts/modules.md)

---

## Database (myfy-data)

### Setup

```python
from myfy.core import Application
from myfy.data import DataModule, Base
from myfy.web import route, WebModule
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

app = Application(auto_discover=False)
app.add_module(DataModule(
    auto_create_tables=True,  # Dev only
    metadata=Base.metadata,
))
app.add_module(WebModule())
```

### CRUD Operations

```python
from sqlalchemy import select

# Create
@route.post("/users", status_code=201)
async def create_user(body: CreateUserDTO, session: AsyncSession) -> dict:
    user = User(name=body.name, email=body.email)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return {"id": user.id, "name": user.name}

# Read
@route.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession) -> dict:
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise errors.NotFound("User not found")
    return {"id": user.id, "name": user.name}

# Update
@route.put("/users/{user_id}")
async def update_user(user_id: int, body: UpdateUserDTO, session: AsyncSession) -> dict:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise errors.NotFound("User not found")
    user.name = body.name
    await session.commit()
    return {"id": user.id, "name": user.name}

# Delete
@route.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int, session: AsyncSession) -> None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise errors.NotFound("User not found")
    await session.delete(user)
    await session.commit()
```

### Database Configuration

```bash
# .env
MYFY_DATA_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
MYFY_DATA_POOL_SIZE=10
MYFY_DATA_MAX_OVERFLOW=20
```

**Supported databases:**

| Database | URL Format |
|----------|------------|
| SQLite | `sqlite+aiosqlite:///./myfy.db` |
| PostgreSQL | `postgresql+asyncpg://user:pass@host/db` |
| MySQL | `mysql+aiomysql://user:pass@host/db` |

[:octicons-arrow-right-24: Data Module](modules/data.md)

---

## Frontend (myfy-frontend)

### Initialize

```bash
uv run myfy frontend init
```

Creates:
- `frontend/templates/` - Jinja2 templates
- `frontend/css/` - Tailwind CSS
- `frontend/js/` - JavaScript
- `package.json` - Node dependencies (Vite, Tailwind 4, DaisyUI 5)

### Render Templates

```python
from myfy.frontend import render_template

@route.get("/")
async def home(request: Request, templates: Jinja2Templates):
    return render_template(
        "home.html",
        request=request,
        templates=templates,
        title="Welcome"
    )
```

### Template Structure

```jinja2
{# templates/home.html #}
{% extends "base.html" %}

{% block content %}
<div class="hero min-h-screen bg-base-200">
  <div class="hero-content text-center">
    <h1 class="text-5xl font-bold">{{ title }}</h1>
    <button class="btn btn-primary">Get Started</button>
  </div>
</div>
{% endblock %}
```

### DaisyUI Components

```html
<!-- Buttons -->
<button class="btn btn-primary">Primary</button>
<button class="btn btn-secondary">Secondary</button>

<!-- Card -->
<div class="card bg-base-100 shadow-xl">
  <div class="card-body">
    <h2 class="card-title">Card Title</h2>
    <p>Card content</p>
  </div>
</div>

<!-- Form -->
<input type="text" class="input input-bordered" />
<button class="btn btn-primary">Submit</button>
```

### Build for Production

```bash
uv run myfy frontend build
```

[:octicons-arrow-right-24: Frontend Module](modules/frontend.md)

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `myfy run` | Start development server |
| `myfy routes` | List all routes |
| `myfy modules` | Show loaded modules |
| `myfy doctor` | Validate configuration |
| `myfy frontend init` | Initialize frontend |
| `myfy frontend build` | Build for production |

### Run Options

```bash
uv run myfy run                    # Default (localhost:8000)
uv run myfy run --port 8080        # Custom port
uv run myfy run --host 0.0.0.0     # Bind all interfaces
uv run myfy run --no-reload        # Disable auto-reload
```

[:octicons-arrow-right-24: CLI Reference](modules/cli.md)

---

## Middleware

```python
from myfy.web import WebModule
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

app.add_module(WebModule(
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"]
        )
    ]
))
```

---

## Testing

### Basic Test

```python
import pytest
from myfy.core import Application

@pytest.fixture
def app():
    return Application(settings_class=TestSettings, auto_discover=False)

def test_repository(app):
    repo = app.container.get(TaskRepository)
    task = repo.create("Test task")
    assert task.id == 1
```

### HTTP Tests

```python
from starlette.testclient import TestClient

def test_get_users(app):
    client = TestClient(app.web_module.get_asgi_app(app.container))
    response = client.get("/users")
    assert response.status_code == 200
```

---

## Common Patterns

### Repository Pattern

```python
class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        return user
```

### Service Layer

```python
class UserService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def get_user(self, user_id: int, session: AsyncSession) -> User:
        repo = UserRepository(session)
        user = await repo.get(user_id)
        if not user:
            raise errors.NotFound(f"User {user_id} not found")
        return user

@provider(scope=SINGLETON)
def user_service(settings: Settings) -> UserService:
    return UserService(settings)
```

### Background Tasks

```python
from starlette.background import BackgroundTask
from starlette.responses import Response

async def send_email_task(to: str, subject: str):
    pass  # Send email

@route.post("/send-email")
async def send_email(body: EmailDTO) -> Response:
    return Response(
        content='{"status": "queued"}',
        background=BackgroundTask(send_email_task, body.to, body.subject)
    )
```

---

## Application Lifecycle

```
Init Phase    →  Load config, create container
Start Phase   →  Start modules in order
Run Phase     →  Execute application
Stop Phase    →  Stop modules in reverse order
```

[:octicons-arrow-right-24: Lifecycle Guide](core-concepts/lifecycle.md)

---

## Project Structure

```
my-project/
├── app.py                    # Application entry
├── .env                      # Environment variables
├── pyproject.toml            # Dependencies
├── services/
│   ├── __init__.py
│   └── user_service.py       # Business logic
├── models/
│   ├── __init__.py
│   └── user.py               # SQLAlchemy models
├── routes/
│   ├── __init__.py
│   └── users.py              # Route handlers
└── frontend/                 # (if using myfy-frontend)
    ├── templates/
    ├── css/
    └── js/
```

---

## Package Installation

```bash
# Full framework (all modules)
pip install myfy

# Individual packages
pip install myfy-core       # Core DI, config, modules
pip install myfy-web        # HTTP/ASGI routing
pip install myfy-data       # Async SQLAlchemy
pip install myfy-frontend   # Tailwind, DaisyUI, Vite
pip install myfy-cli        # Development commands
```

---

## Deep Dives

| Topic | Link |
|-------|------|
| Dependency Injection | [Core Concepts: DI](core-concepts/dependency-injection.md) |
| Module System | [Core Concepts: Modules](core-concepts/modules.md) |
| Configuration | [Core Concepts: Configuration](core-concepts/configuration.md) |
| Application Lifecycle | [Core Concepts: Lifecycle](core-concepts/lifecycle.md) |
| Web Module | [Modules: Web](modules/web.md) |
| Data Module | [Modules: Data](modules/data.md) |
| Frontend Module | [Modules: Frontend](modules/frontend.md) |
| CLI Tools | [Modules: CLI](modules/cli.md) |
| Full Tutorial | [Getting Started: Tutorial](getting-started/tutorial.md) |
