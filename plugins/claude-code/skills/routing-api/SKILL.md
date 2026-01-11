---
name: routing-api
description: myfy web routing with FastAPI-like decorators. Use when working with @route decorators, path parameters, query parameters, request bodies, authentication, or error handling.
---

# Web Routing in myfy

myfy provides FastAPI-like routing with full DI integration.

## Route Decorators

```python
from myfy.web import route

@route.get("/path")
async def handler() -> dict:
    return {"message": "hello"}

@route.post("/path", status_code=201)
async def create() -> dict:
    return {"created": True}

@route.put("/path/{id}")
async def update(id: int) -> dict:
    return {"updated": id}

@route.delete("/path/{id}", status_code=204)
async def delete(id: int) -> None:
    pass

@route.patch("/path/{id}")
async def partial_update(id: int) -> dict:
    return {"patched": id}
```

## Path Parameters

Extract from URL template using `{param}`:

```python
@route.get("/users/{user_id}/posts/{post_id}")
async def get_post(user_id: int, post_id: int) -> dict:
    return {"user": user_id, "post": post_id}
```

Path parameters are:
- Automatically type-converted based on annotation
- Must match function parameter names exactly
- Must be valid Python identifiers

## Query Parameters

Use `Query` for explicit query parameters:

```python
from myfy.web import Query

@route.get("/search")
async def search(
    q: str = Query(default=""),           # With default value
    limit: int = Query(default=10),       # Integer query param
    page: int = Query(alias="p"),         # Aliased (?p=1 in URL)
) -> dict:
    return {"query": q, "limit": limit, "page": page}
```

## Request Body

Use Pydantic models or dataclasses for request bodies:

```python
from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    name: str

@route.post("/users", status_code=201)
async def create_user(body: UserCreate, session: AsyncSession) -> dict:
    user = User(**body.model_dump())
    session.add(user)
    await session.commit()
    return {"id": user.id}
```

Request bodies are automatically:
- Parsed from JSON
- Validated by Pydantic
- Type-checked at runtime

## Parameter Classification

Parameters are classified in this order:

1. **Path parameters** - Names matching `{param}` in route path
2. **Query parameters** - Annotated with `Query(...)`
3. **Body parameter** - Pydantic model, dataclass, or dict
4. **DI dependencies** - Everything else (resolved from container)

```python
@route.post("/users/{user_id}/orders")
async def create_order(
    user_id: int,                    # 1. Path param (matches {user_id})
    limit: int = Query(default=10),  # 2. Query param (explicit Query)
    body: OrderCreate,               # 3. Request body (Pydantic model)
    session: AsyncSession,           # 4. DI dependency
    settings: AppSettings,           # 4. DI dependency
) -> dict:
    ...
```

## Authentication

Use `Authenticated` for protected routes:

```python
from myfy.web import Authenticated, AuthModule
from dataclasses import dataclass

@dataclass
class User(Authenticated):
    email: str

# Register auth provider
def my_auth(request: Request) -> User | None:
    token = request.headers.get("Authorization")
    if not token:
        return None  # Results in 401
    return User(id="123", email="user@example.com")

app.add_module(AuthModule(authenticated_provider=my_auth))

# Protected route - returns 401 if not authenticated
@route.get("/profile")
async def profile(user: User) -> dict:
    return {"id": user.id, "email": user.email}
```

## Error Handling

### Quick Errors with abort()

```python
from myfy.web import abort

@route.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession) -> dict:
    user = await session.get(User, user_id)
    if not user:
        abort(404, "User not found")
    return {"user": user}
```

### Typed Errors

```python
from myfy.web import errors

raise errors.NotFound("User not found")
raise errors.BadRequest("Invalid email", field="email")
raise errors.Unauthorized("Invalid token")
raise errors.Forbidden("Access denied")
raise errors.Conflict("Email already exists")
```

### Custom Exceptions

```python
from myfy.web.exceptions import WebError

class RateLimitExceeded(WebError):
    status_code = 429
    error_type = "rate_limit_exceeded"
```

## Rate Limiting

```python
from myfy.web.ratelimit import RateLimitModule, rate_limit, RateLimitKey

# Add module
app.add_module(RateLimitModule())

# Rate limit by IP (default)
@route.get("/api/data")
@rate_limit(100)  # 100 requests per minute per IP
async def get_data() -> dict:
    ...

# Rate limit by authenticated user
@route.get("/api/profile")
@rate_limit(50, key=RateLimitKey.USER)
async def get_profile(user: User) -> dict:
    ...
```

## Response Types

Routes can return:

```python
# Dict (serialized to JSON)
@route.get("/json")
async def json_response() -> dict:
    return {"key": "value"}

# Pydantic model (serialized to JSON)
@route.get("/model")
async def model_response() -> UserResponse:
    return UserResponse(id=1, name="John")

# None for 204 No Content
@route.delete("/users/{id}", status_code=204)
async def delete_user(id: int) -> None:
    ...
```

## Best Practices

1. **Always use async** - All handlers should be async functions
2. **Type all parameters** - Use type hints for auto-classification
3. **Use Pydantic for bodies** - Get free validation
4. **Return typed responses** - Prefer Pydantic models over dicts
5. **Use appropriate status codes** - 201 for creation, 204 for deletion
6. **Handle errors explicitly** - Use abort() or typed errors
7. **Document with docstrings** - Add OpenAPI-compatible docs
