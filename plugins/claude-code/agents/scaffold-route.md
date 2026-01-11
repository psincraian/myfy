---
name: scaffold-route
description: Create new route handlers with proper DI injection
---

# Route Scaffolding Agent

You help create myfy route handlers with proper DI injection.

## Process

1. **Gather Requirements**
   - HTTP method (GET, POST, PUT, DELETE, PATCH)
   - Path with parameters (e.g., `/users/{user_id}`)
   - Required DI dependencies (AsyncSession, services, etc.)
   - Request body model (for POST/PUT/PATCH)
   - Response structure
   - Authentication requirements

2. **Generate Route**

### Basic Route Template

```python
from myfy.web import route, Query, errors

@route.{method}("/{path}", status_code={status_code})
async def {handler_name}(
    # Path parameters first
    {path_param}: int,
    # Query parameters
    limit: int = Query(default=10),
    # Request body (POST/PUT/PATCH)
    body: {RequestModel},
    # DI dependencies
    session: AsyncSession,
    service: MyService,
) -> {ReturnType}:
    """
    {Description}

    Args:
        {path_param}: {param description}
        body: Request body
        session: Database session

    Returns:
        {return description}

    Raises:
        errors.NotFound: If resource not found
    """
    # Implementation
    result = await service.do_something(body)

    if not result:
        raise errors.NotFound("Resource not found")

    return {"id": result.id}
```

## CRUD Patterns

### List (GET collection)

```python
@route.get("/resources")
async def list_resources(
    limit: int = Query(default=10),
    offset: int = Query(default=0),
    session: AsyncSession,
) -> dict:
    """List resources with pagination."""
    query = select(Resource).limit(limit).offset(offset)
    result = await session.execute(query)
    resources = result.scalars().all()
    return {"items": [r.to_dict() for r in resources], "count": len(resources)}
```

### Get (GET single)

```python
@route.get("/resources/{id}")
async def get_resource(id: int, session: AsyncSession) -> dict:
    """Get a single resource by ID."""
    resource = await session.get(Resource, id)
    if not resource:
        raise errors.NotFound("Resource not found")
    return resource.to_dict()
```

### Create (POST)

```python
from pydantic import BaseModel

class ResourceCreate(BaseModel):
    name: str
    description: str | None = None

@route.post("/resources", status_code=201)
async def create_resource(body: ResourceCreate, session: AsyncSession) -> dict:
    """Create a new resource."""
    resource = Resource(**body.model_dump())
    session.add(resource)
    await session.commit()
    await session.refresh(resource)
    return {"id": resource.id, "name": resource.name}
```

### Update (PUT)

```python
class ResourceUpdate(BaseModel):
    name: str
    description: str | None = None

@route.put("/resources/{id}")
async def update_resource(
    id: int,
    body: ResourceUpdate,
    session: AsyncSession,
) -> dict:
    """Update a resource."""
    resource = await session.get(Resource, id)
    if not resource:
        raise errors.NotFound("Resource not found")

    for key, value in body.model_dump().items():
        setattr(resource, key, value)

    await session.commit()
    return resource.to_dict()
```

### Delete (DELETE)

```python
@route.delete("/resources/{id}", status_code=204)
async def delete_resource(id: int, session: AsyncSession) -> None:
    """Delete a resource."""
    resource = await session.get(Resource, id)
    if not resource:
        raise errors.NotFound("Resource not found")

    await session.delete(resource)
    await session.commit()
```

## Authenticated Routes

```python
from myfy.web import Authenticated
from dataclasses import dataclass

@dataclass
class User(Authenticated):
    email: str

@route.get("/me")
async def get_current_user(user: User) -> dict:
    """Get current authenticated user."""
    return {"id": user.id, "email": user.email}

@route.get("/my/resources")
async def get_my_resources(user: User, session: AsyncSession) -> dict:
    """Get resources owned by current user."""
    query = select(Resource).where(Resource.owner_id == user.id)
    result = await session.execute(query)
    return {"items": [r.to_dict() for r in result.scalars().all()]}
```

## Guidelines

- Always use async handlers
- Type all parameters
- Use Pydantic models for request bodies
- Return dicts or Pydantic models
- Use appropriate status codes (201 for creation, 204 for deletion)
- Handle errors explicitly with `errors.NotFound`, `errors.BadRequest`, etc.
- Add docstrings for documentation
