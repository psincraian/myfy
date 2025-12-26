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

### Rate Limiting

Flexible rate limiting with decorator and middleware support:

```python
from myfy.web import route
from myfy.web.ratelimit import rate_limit, RateLimitKey

@route.get("/api/data")
@rate_limit(100, key=RateLimitKey.IP)  # 100 req/min per IP
async def get_data() -> dict:
    return {"data": "value"}
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

For custom exception handling, use Starlette's exception handler mechanism by extending the ASGI app after creation:

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

# Add exception handlers after creating the app
app = Application(auto_discover=False)
app.add_module(WebModule())
app.initialize()

# Get the ASGI app and add handlers
web_module = app.get_module(WebModule)
asgi_app = web_module.get_asgi_app(app.container)
asgi_app.app.add_exception_handler(CustomError, custom_error_handler)
```

## Rate Limiting

myfy-web includes a flexible rate limiting system with middleware for global protection and decorators for per-route customization.

### Basic Usage

Use the `@rate_limit` decorator to add rate limits to specific routes:

```python
from myfy.web import route
from myfy.web.ratelimit import rate_limit

@route.get("/api/data")
@rate_limit(100)  # 100 requests per 60 seconds
async def get_data() -> dict:
    return {"data": "value"}

@route.post("/api/expensive")
@rate_limit(10, window_seconds=3600)  # 10 requests per hour
async def expensive_operation() -> dict:
    return {"result": "done"}
```

### Key Strategies

Rate limit by different identifiers using `RateLimitKey`:

```python
from myfy.web.ratelimit import rate_limit, RateLimitKey

# Rate limit by client IP (default)
@rate_limit(100, key=RateLimitKey.IP)
async def by_ip(): ...

# Rate limit by user ID (requires authentication)
@rate_limit(100, key=RateLimitKey.USER)
async def by_user(): ...

# Rate limit by API key header
@rate_limit(100, key=RateLimitKey.API_KEY)
async def by_api_key(): ...

# Rate limit by session ID
@rate_limit(100, key=RateLimitKey.SESSION)
async def by_session(): ...

# Rate limit by endpoint (same limit for all clients)
@rate_limit(1000, key=RateLimitKey.ENDPOINT)
async def by_endpoint(): ...

# Custom key string
@rate_limit(100, key="custom:bucket")
async def custom_key(): ...
```

**Available keys:**

| Key | Description |
|-----|-------------|
| `RateLimitKey.IP` | Client IP address (default) |
| `RateLimitKey.USER` | Authenticated user ID |
| `RateLimitKey.API_KEY` | X-API-Key header value |
| `RateLimitKey.SESSION` | Session ID from cookie |
| `RateLimitKey.ENDPOINT` | Route path (shared by all clients) |
| `RateLimitKey.GLOBAL` | Single global counter |

### Dynamic Key Override

Inject `RateLimitContext` to override keys based on business logic:

```python
from myfy.web import route
from myfy.web.ratelimit import rate_limit, RateLimitContext

@route.get("/api/org/{org_id}/data")
@rate_limit(100)
async def get_org_data(org_id: int, rl: RateLimitContext) -> dict:
    # Rate limit by organization instead of IP
    rl.override_key(f"org:{org_id}")
    return {"org_id": org_id, "data": "value"}

@route.get("/api/premium")
@rate_limit(100)
async def premium_endpoint(user: User, rl: RateLimitContext) -> dict:
    # Different limits for different tiers
    if user.is_premium:
        rl.override_key(f"premium:{user.id}")
    else:
        rl.override_key(f"free:{user.id}")
    return {"data": "premium content"}
```

### Skip Rate Limiting

Skip rate limiting for specific requests:

```python
@route.get("/api/health")
@rate_limit(100)
async def health_check(rl: RateLimitContext) -> dict:
    # Skip rate limiting for internal health checks
    rl.skip()
    return {"status": "ok"}
```

### Scoped Rate Limits

Group routes under the same rate limit bucket:

```python
# Both routes share the same rate limit bucket
@route.get("/api/v1/users")
@rate_limit(100, scope="users-api")
async def list_users(): ...

@route.get("/api/v1/users/{id}")
@rate_limit(100, scope="users-api")
async def get_user(id: int): ...
```

### Module Setup

Add the `RateLimitModule` for automatic middleware integration:

```python
from myfy.core import Application
from myfy.web import WebModule
from myfy.web.ratelimit import RateLimitModule, RateLimitSettings

settings = RateLimitSettings(
    enabled=True,
    default_requests=100,
    default_window_seconds=60,
    global_requests=1000,
    global_window_seconds=60,
)

app = Application(auto_discover=False)
app.add_module(WebModule())
app.add_module(RateLimitModule(settings=settings))
```

### Configuration

Configure via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MYFY_RATELIMIT_ENABLED` | `true` | Enable/disable rate limiting |
| `MYFY_RATELIMIT_DEFAULT_REQUESTS` | `100` | Default requests per window |
| `MYFY_RATELIMIT_DEFAULT_WINDOW_SECONDS` | `60` | Default window in seconds |
| `MYFY_RATELIMIT_GLOBAL_REQUESTS` | `1000` | Global limit (all routes) |
| `MYFY_RATELIMIT_GLOBAL_WINDOW_SECONDS` | `60` | Global window in seconds |
| `MYFY_RATELIMIT_INCLUDE_HEADERS` | `true` | Include X-RateLimit-* headers |

Or via `RateLimitSettings`:

```python
from myfy.web.ratelimit import RateLimitSettings, RateLimitKey

settings = RateLimitSettings(
    enabled=True,
    default_requests=100,
    default_window_seconds=60,
    default_key=RateLimitKey.IP,
    global_requests=1000,
    global_window_seconds=60,
    include_headers=True,
    backend="memory",  # "memory" or "redis"
)
```

### Response Headers

When `include_headers=True`, responses include rate limit headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1703520000
```

When rate limited (HTTP 429):

```
Retry-After: 30
```

### Error Response Format

Rate limit errors follow RFC 7807 Problem Details:

```json
{
    "type": "rate_limit_exceeded",
    "title": "Rate Limit Exceeded",
    "status": 429,
    "detail": "Rate limit exceeded. Please retry after 30 seconds.",
    "retry_after": 30
}
```

### Manual Middleware Setup

For fine-grained control, add middleware directly:

```python
from myfy.web import WebModule
from myfy.web.ratelimit import (
    RateLimitMiddleware,
    RateLimitSettings,
    InMemoryRateLimitStore,
)
from starlette.middleware import Middleware

store = InMemoryRateLimitStore()
settings = RateLimitSettings(enabled=True)

app.add_module(WebModule(
    middleware=[
        Middleware(RateLimitMiddleware, store=store, settings=settings)
    ]
))
```

### Custom Storage Backend

Implement `RateLimitStore` for custom backends (e.g., Redis):

```python
from myfy.web.ratelimit import RateLimitStore, RateLimitResult

class RedisRateLimitStore:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def check_and_increment(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        # Implement sliding window counter with Redis
        ...

    async def get_remaining(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        ...

    async def reset(self, key: str) -> None:
        await self.redis.delete(key)
```

## WebModule Configuration

Configure the WebModule with a custom router and middleware:

```python
from myfy.web import WebModule, Router
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# Custom router (optional)
custom_router = Router()

app.add_module(WebModule(
    router=custom_router,        # Custom router (optional)
    middleware=[                 # Custom middleware (optional)
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"]
        )
    ]
))
```

**Server configuration** is done via environment variables or WebSettings:

```bash
# .env
MYFY_WEB_HOST=0.0.0.0
MYFY_WEB_PORT=8000
MYFY_WEB_CORS_ENABLED=true
MYFY_WEB_CORS_ALLOWED_ORIGINS=["https://example.com"]
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
