# myfy-web

HTTP/Web module for myfy with FastAPI-style routing and dependency injection.

## Overview

`myfy-web` provides a powerful web framework built on top of Starlette, with FastAPI-inspired decorators and deep integration with myfy's dependency injection system.

## Installation

```bash
# Install web module
pip install myfy-web

# Or with uv
uv pip install myfy-web
```

**Dependencies:**
- `myfy-core` - Core framework
- `starlette` - ASGI toolkit
- `uvicorn` - ASGI server

## Key Features

### FastAPI-Style Routes

Decorator-based routing with automatic parameter injection:

```python
from myfy.web import route

@route.get("/users/{user_id}")
async def get_user(user_id: int) -> dict:
    return {"id": user_id, "name": "John"}
```

### Dependency Injection in Routes

Mix path parameters, body parsing, and DI seamlessly:

```python
from myfy.web import route
from myfy.core import provider, SINGLETON

@provider(scope=SINGLETON)
def user_service() -> UserService:
    return UserService()

@route.get("/users/{user_id}")
async def get_user(user_id: int, service: UserService) -> User:
    # user_id from path, service injected
    return await service.get_user(user_id)
```

### Request Body Parsing

Automatic validation with Pydantic:

```python
from pydantic import BaseModel

class CreateUserDTO(BaseModel):
    name: str
    email: str

@route.post("/users")
async def create_user(body: CreateUserDTO, service: UserService) -> User:
    return await service.create_user(body)
```

### WebModule

The main module that provides HTTP server functionality:

```python
from myfy.core import Application
from myfy.web import WebModule

app = Application(auto_discover=False)
app.add_module(WebModule())
```

## Quick Start

### Basic Application

```python
from myfy.core import Application
from myfy.web import route, WebModule

@route.get("/")
async def home() -> dict:
    return {"message": "Hello World"}

@route.get("/hello/{name}")
async def hello(name: str) -> dict:
    return {"message": f"Hello {name}!"}

app = Application(auto_discover=False)
app.add_module(WebModule())

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run())
```

Run with:
```bash
uv run myfy run
```

### Application with DI

```python
from myfy.core import Application, provider, SINGLETON, BaseSettings
from myfy.web import route, WebModule
from pydantic import Field

# Settings
class Settings(BaseSettings):
    app_name: str = Field(default="My App")
    api_version: str = Field(default="1.0.0")

# Service
class GreetingService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def greet(self, name: str) -> str:
        return f"Hello {name} from {self.settings.app_name}!"

@provider(scope=SINGLETON)
def greeting_service(settings: Settings) -> GreetingService:
    return GreetingService(settings)

# Routes
@route.get("/")
async def home(service: GreetingService) -> dict:
    return {"message": service.greet("World")}

@route.get("/greet/{name}")
async def greet(name: str, service: GreetingService) -> dict:
    return {"message": service.greet(name)}

# App
app = Application(settings_class=Settings, auto_discover=False)
app.add_module(WebModule())
```

## Route Decorators

### HTTP Methods

```python
from myfy.web import route

@route.get("/users")          # GET
async def list_users(): ...

@route.post("/users")         # POST
async def create_user(): ...

@route.put("/users/{id}")     # PUT
async def update_user(): ...

@route.patch("/users/{id}")   # PATCH
async def partial_update(): ...

@route.delete("/users/{id}")  # DELETE
async def delete_user(): ...
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

```python
@route.get("/users")
async def list_users(
    page: int = 1,
    limit: int = 10,
    sort: str = "name"
) -> list[User]:
    return await service.list_users(page, limit, sort)

# Call with: GET /users?page=2&limit=20&sort=created_at
```

### Query Parameters with Validation

Use `Query()` for built-in validation constraints:

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

**Available constraints:**

| Constraint | Type | Description |
|------------|------|-------------|
| `default` | Any | Default value (use `...` for required) |
| `ge` | int/float | Greater than or equal |
| `le` | int/float | Less than or equal |
| `gt` | int/float | Greater than |
| `lt` | int/float | Less than |
| `min_length` | int | Minimum string length |
| `max_length` | int | Maximum string length |
| `pattern` | str | Regex pattern for validation |
| `alias` | str | Alternative query param name |
| `description` | str | Parameter description for docs |

### Request Body

```python
from pydantic import BaseModel, Field

class CreateUserDTO(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    age: int = Field(ge=0, le=150)

@route.post("/users")
async def create_user(body: CreateUserDTO) -> User:
    # body automatically parsed and validated
    return await service.create_user(body)
```

## Response Types

### JSON (Default)

```python
@route.get("/user")
async def get_user() -> dict:
    return {"id": 1, "name": "John"}
    # Returns: 200 with application/json
```

### Pydantic Models

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str

@route.get("/user")
async def get_user() -> User:
    return User(id=1, name="John")
    # Automatically serialized to JSON
```

### Custom Responses

```python
from starlette.responses import Response, RedirectResponse

@route.get("/redirect")
async def redirect():
    return RedirectResponse(url="/home")

@route.get("/custom")
async def custom():
    return Response(
        content="Custom response",
        media_type="text/plain"
    )
```

## Middleware

Add custom middleware to the WebModule:

```python
from myfy.web import WebModule
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

app = Application(auto_discover=False)
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

## Exception Handling

### WebError Hierarchy

myfy provides a built-in exception hierarchy with RFC 7807 Problem Details format:

```python
from myfy.web import errors

@route.get("/users/{user_id}")
async def get_user(user_id: int) -> User:
    user = await service.get_user(user_id)
    if not user:
        raise errors.NotFound("User not found")
    return user
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

### Errors with Extra Fields

Include additional context in your errors:

```python
raise errors.NotFound("User not found", user_id=user_id)
raise errors.BadRequest("Invalid email format", field="email")
raise errors.Conflict("Username already taken", username="john_doe")
raise errors.RateLimit("Too many requests", retry_after=60)
```

These produce RFC 7807 Problem Details responses:

```json
{
    "type": "not_found",
    "title": "NotFoundError",
    "status": 404,
    "detail": "User not found",
    "user_id": 123
}
```

### Custom Errors

Create domain-specific errors by subclassing `WebError`:

```python
from myfy.web.exceptions import WebError

class PaymentRequiredError(WebError):
    status_code = 402
    error_type = "payment_required"

class InsufficientCreditsError(WebError):
    status_code = 402
    error_type = "insufficient_credits"

# Usage
raise PaymentRequiredError("Payment required to access this feature")
raise InsufficientCreditsError("Insufficient credits", required=100, current=25)
```

### HTTP Exceptions (Legacy)

You can still use Starlette's HTTPException:

```python
from starlette.exceptions import HTTPException

@route.get("/users/{user_id}")
async def get_user(user_id: int) -> User:
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### Custom Exception Handlers

```python
from starlette.requests import Request
from starlette.responses import JSONResponse

class CustomError(Exception):
    pass

async def custom_error_handler(request: Request, exc: CustomError):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)}
    )

app.add_module(WebModule(
    exception_handlers={
        CustomError: custom_error_handler
    }
))
```

## WebModule Configuration

Configure the WebModule with custom settings:

```python
from myfy.web import WebModule
from starlette.middleware import Middleware

app.add_module(WebModule(
    host="0.0.0.0",              # Bind address
    port=8000,                   # Port number
    middleware=[...],            # Custom middleware
    exception_handlers={...},    # Exception handlers
    debug=True                   # Debug mode
))
```

## Common Patterns

### CRUD API

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str

class CreateUserDTO(BaseModel):
    name: str
    email: str

class UpdateUserDTO(BaseModel):
    name: str | None = None
    email: str | None = None

# List
@route.get("/users")
async def list_users(service: UserService) -> list[User]:
    return await service.list_all()

# Get
@route.get("/users/{user_id}")
async def get_user(user_id: int, service: UserService) -> User:
    user = await service.get(user_id)
    if not user:
        raise HTTPException(status_code=404)
    return user

# Create
@route.post("/users", status_code=201)
async def create_user(body: CreateUserDTO, service: UserService) -> User:
    return await service.create(body)

# Update
@route.put("/users/{user_id}")
async def update_user(
    user_id: int,
    body: UpdateUserDTO,
    service: UserService
) -> User:
    user = await service.update(user_id, body)
    if not user:
        raise HTTPException(status_code=404)
    return user

# Delete
@route.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int, service: UserService) -> None:
    deleted = await service.delete(user_id)
    if not deleted:
        raise HTTPException(status_code=404)
```

### Pagination

```python
from pydantic import BaseModel

class PaginatedResponse(BaseModel):
    items: list[User]
    page: int
    per_page: int
    total: int

@route.get("/users")
async def list_users(
    page: int = 1,
    per_page: int = 20,
    service: UserService = None
) -> PaginatedResponse:
    items, total = await service.paginate(page, per_page)
    return PaginatedResponse(
        items=items,
        page=page,
        per_page=per_page,
        total=total
    )
```

### File Uploads

```python
from starlette.requests import Request

@route.post("/upload")
async def upload_file(request: Request) -> dict:
    form = await request.form()
    file = form["file"]

    contents = await file.read()
    filename = file.filename

    # Process file...

    return {"filename": filename, "size": len(contents)}
```

### Background Tasks

```python
from starlette.background import BackgroundTask

async def send_email(email: str, message: str):
    # Send email asynchronously
    pass

@route.post("/send")
async def send_notification(email: str, message: str):
    return Response(
        content="Email will be sent",
        background=BackgroundTask(send_email, email, message)
    )
```

## Best Practices

### Use DTOs for Input

```python
# ✓ Good - Explicit validation
class CreateUserDTO(BaseModel):
    name: str = Field(min_length=1)
    email: str

@route.post("/users")
async def create_user(body: CreateUserDTO):
    pass

# ✗ Bad - No validation
@route.post("/users")
async def create_user(name: str, email: str):
    pass
```

### Return Pydantic Models

```python
# ✓ Good - Type-safe serialization
@route.get("/user")
async def get_user() -> User:
    return User(id=1, name="John")

# ✗ Bad - Manual dict construction
@route.get("/user")
async def get_user() -> dict:
    return {"id": 1, "name": "John"}
```

### Use Appropriate HTTP Status Codes

```python
# ✓ Good
@route.post("/users", status_code=201)  # Created
@route.delete("/users/{id}", status_code=204)  # No Content

# ✗ Bad
@route.post("/users")  # Returns 200 instead of 201
@route.delete("/users/{id}")  # Returns 200 with empty body
```

### Handle Errors Gracefully

```python
# ✓ Good
@route.get("/users/{id}")
async def get_user(id: int) -> User:
    user = await service.get(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# ✗ Bad - Let exceptions bubble up
@route.get("/users/{id}")
async def get_user(id: int) -> User:
    return await service.get(id)  # May return None
```

## Examples

See the [Tutorial](../getting-started/tutorial.md) for a complete CRUD API example.

## Next Steps

- **Add Frontend**: Install [`myfy-frontend`](frontend.md) for UI templates
- **Add CLI**: Install [`myfy-cli`](cli.md) for development tools
