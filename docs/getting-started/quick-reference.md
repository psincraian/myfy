# Quick Reference

Fast lookups for common myfy patterns.

---

## Application Setup

### Basic Application

```python
from myfy.core import Application, BaseSettings
from myfy.web import WebModule

class Settings(BaseSettings):
    app_name: str = "My App"

app = Application(settings_class=Settings, auto_discover=False)
app.add_module(WebModule())
```

### With Auto-Discovery

```python
# Automatically discovers modules via entry points
app = Application(settings_class=Settings, auto_discover=True)
```

---

## Dependency Injection

### Register Provider

```python
from myfy.core import provider, SINGLETON, REQUEST

@provider(scope=SINGLETON)
def database(settings: Settings) -> Database:
    return Database(settings.db_url)

@provider(scope=REQUEST)
def session(db: Database) -> Session:
    return db.create_session()
```

### Inject Dependencies

```python
# In routes
@route.get("/users")
async def list_users(db: Database) -> list[User]:
    return await db.get_all_users()

# In other providers
@provider(scope=SINGLETON)
def user_service(db: Database, cache: Cache) -> UserService:
    return UserService(db, cache)
```

### Scopes

| Scope | Lifetime | Use Case |
|-------|----------|----------|
| `SINGLETON` | Application | Database connections, caches |
| `REQUEST` | HTTP Request | Database sessions, request context |
| `TASK` | Background Task | Task-specific resources |

---

## Configuration

### Basic Settings

```python
from myfy.core import BaseSettings
from pydantic import Field

class AppSettings(BaseSettings):
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
# Use dev profile
MYFY_PROFILE=dev uv run myfy run

# Use prod profile
MYFY_PROFILE=prod uv run myfy run
```

---

## Web Routes

### Basic Routes

```python
from myfy.web import route

@route.get("/")
async def index() -> dict:
    return {"message": "Hello"}

@route.get("/users/{user_id}")
async def get_user(user_id: int) -> User:
    return await db.get_user(user_id)

@route.post("/users")
async def create_user(body: CreateUserDTO) -> User:
    return await db.create_user(body)
```

### HTTP Methods

```python
@route.get("/resource")      # GET
@route.post("/resource")     # POST
@route.put("/resource/{id}") # PUT
@route.patch("/resource/{id}") # PATCH
@route.delete("/resource/{id}") # DELETE
```

### Status Codes

```python
@route.post("/users", status_code=201)
async def create_user(body: CreateUserDTO) -> User:
    return await db.create_user(body)

@route.delete("/users/{id}", status_code=204)
async def delete_user(user_id: int) -> None:
    await db.delete_user(user_id)
```

### Path Parameters

```python
@route.get("/posts/{post_id}/comments/{comment_id}")
async def get_comment(post_id: int, comment_id: int) -> Comment:
    return await db.get_comment(post_id, comment_id)
```

### Request Body

```python
from pydantic import BaseModel

class CreateUser(BaseModel):
    name: str
    email: str

@route.post("/users")
async def create_user(body: CreateUser, db: Database) -> User:
    return await db.create_user(body)
```

### Query Parameters

```python
# Coming soon - use Starlette's Request for now
@route.get("/search")
async def search(request: Request) -> list[Result]:
    query = request.query_params.get("q", "")
    return await search_engine.search(query)
```

---

## Modules

### Create Module

```python
from myfy.core import BaseModule, Container

class DataModule(BaseModule):
    def __init__(self):
        super().__init__("data")

    def configure(self, container: Container) -> None:
        # Register providers
        container.register(Database, factory=create_db, scope=SINGLETON)

    async def start(self) -> None:
        # Startup logic
        self.db = await connect_database()

    async def stop(self) -> None:
        # Cleanup logic
        await self.db.disconnect()
```

### Register Module

```python
app.add_module(DataModule())
app.add_module(WebModule())
```

---

## CLI Commands

### Run Server

```bash
# Default (port 8000, auto-reload)
uv run myfy run

# Custom port
uv run myfy run --port 8001

# No reload
uv run myfy run --reload false

# Custom host
uv run myfy run --host 0.0.0.0 --port 8080
```

### List Routes

```bash
uv run myfy routes
```

### Show Modules

```bash
uv run myfy modules
```

### Validate Config

```bash
uv run myfy doctor
```

---

## Error Handling

### HTTP Exceptions

```python
from starlette.exceptions import HTTPException

@route.get("/users/{user_id}")
async def get_user(user_id: int, db: Database) -> User:
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### Custom Exception Handler

```python
from starlette.requests import Request
from starlette.responses import JSONResponse

async def custom_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)}
    )

# Register in WebModule (advanced)
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

### Override Dependencies

```python
@pytest.fixture
def app():
    app = Application(settings_class=TestSettings, auto_discover=False)

    # Override provider
    @provider(scope=SINGLETON)
    def mock_database() -> Database:
        return MockDatabase()

    return app
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

## Pydantic Models

### Request DTOs

```python
from pydantic import BaseModel, Field, validator

class CreateUserDTO(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    age: int = Field(ge=18, le=120)

    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('must be alphanumeric')
        return v
```

### Response Models

```python
from datetime import datetime

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True  # For SQLAlchemy models
```

---

## Async Patterns

### Async Handler

```python
@route.get("/users")
async def list_users(db: Database) -> list[User]:
    # Use await for async operations
    users = await db.get_all_users()
    return users
```

### Sync Handler

```python
@route.get("/config")
def get_config(settings: Settings) -> dict:
    # Sync handlers work too (but prefer async)
    return {"app_name": settings.app_name}
```

### Background Tasks

```python
# Coming soon - use Starlette's BackgroundTasks for now
from starlette.background import BackgroundTasks

@route.post("/send-email")
async def send_email(
    body: EmailDTO,
    background_tasks: BackgroundTasks
) -> dict:
    background_tasks.add_task(send_email_task, body.to, body.subject)
    return {"status": "queued"}
```

---

## Common Patterns

### Repository Pattern

```python
class UserRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get(self, user_id: int) -> User | None:
        return await self.db.get_user(user_id)

    async def list_all(self) -> list[User]:
        return await self.db.get_all_users()

    async def create(self, data: CreateUserDTO) -> User:
        return await self.db.create_user(data)

@provider(scope=SINGLETON)
def user_repository(db: Database) -> UserRepository:
    return UserRepository(db)
```

### Service Layer

```python
class UserService:
    def __init__(self, repo: UserRepository, cache: Cache):
        self.repo = repo
        self.cache = cache

    async def get_user(self, user_id: int) -> User:
        # Check cache
        cached = await self.cache.get(f"user:{user_id}")
        if cached:
            return User.model_validate(cached)

        # Get from database
        user = await self.repo.get(user_id)
        if user:
            await self.cache.set(f"user:{user_id}", user.model_dump())

        return user

@provider(scope=SINGLETON)
def user_service(repo: UserRepository, cache: Cache) -> UserService:
    return UserService(repo, cache)
```

### Factory Pattern

```python
class DatabaseFactory:
    @staticmethod
    def create(settings: Settings) -> Database:
        if settings.db_type == "postgres":
            return PostgresDatabase(settings.db_url)
        elif settings.db_type == "mysql":
            return MySQLDatabase(settings.db_url)
        else:
            raise ValueError(f"Unknown db_type: {settings.db_type}")

@provider(scope=SINGLETON)
def database(settings: Settings) -> Database:
    return DatabaseFactory.create(settings)
```

---

## Environment Variables

### Common Variables

```bash
# Application
APP_NAME=My App
DEBUG=true

# Database
DATABASE_URL=postgresql://localhost/mydb
DB_POOL_SIZE=10

# Redis
REDIS_URL=redis://localhost:6379

# API Keys
API_KEY=your-secret-key
JWT_SECRET=your-jwt-secret

# Profiles
MYFY_PROFILE=dev  # Use .env.dev
```

---

## Type Hints

### Common Types

```python
from typing import Optional, List, Dict, Any

# Optional
user: User | None = None

# List
users: list[User] = []

# Dict
config: dict[str, Any] = {}

# Multiple types
result: User | dict[str, Any] = get_result()
```

---

## Next Steps

- [Core Concepts](../core-concepts/dependency-injection.md) - Deep dive
- [Testing Guide](../guides/testing.md) - Test your app
- [Deployment](../guides/deployment.md) - Go to production
