---
name: scaffold-provider
description: Create new DI providers with correct scopes
---

# Provider Scaffolding Agent

You help create myfy DI providers with correct scope selection.

## Scope Selection Guide

| Scope | When to Use | Examples |
|-------|-------------|----------|
| SINGLETON | Shared, stateless, expensive to create | Config, pools, HTTP clients, caches |
| REQUEST | Per-request state, database sessions | DB sessions, user context, request logger |
| TASK | Per-background-job state | Task logger, job-specific clients |

## Process

1. **Determine Scope**
   - Does it hold request-specific state? -> REQUEST
   - Is it shared across all requests? -> SINGLETON
   - Is it for background tasks? -> TASK

2. **Generate Provider**

### SINGLETON Provider

```python
from myfy.core import provider, SINGLETON

@provider(scope=SINGLETON)
def email_service(settings: AppSettings) -> EmailService:
    """
    Create email service singleton.

    This is created once at startup and shared across all requests.
    """
    return EmailService(
        api_key=settings.email_api_key,
        from_address=settings.email_from,
    )
```

### REQUEST Provider

```python
from myfy.core import provider, REQUEST
from myfy.data import AsyncSession

@provider(scope=REQUEST)
def user_repository(session: AsyncSession) -> UserRepository:
    """
    Create user repository for this request.

    Created per-request, uses the request-scoped session.
    Automatically cleaned up after request completes.
    """
    return UserRepository(session)
```

### TASK Provider

```python
from myfy.core import provider, TASK
from myfy.tasks import TaskContext

@provider(scope=TASK)
def task_notifier(ctx: TaskContext, settings: AppSettings) -> TaskNotifier:
    """
    Create notifier for this background task.

    Created per-task execution, has access to task context.
    """
    return TaskNotifier(task_id=ctx.task_id, webhook_url=settings.webhook_url)
```

## Common Patterns

### Factory Pattern (for REQUEST-scoped from SINGLETON)

When you need REQUEST-scoped instances but the configuration is SINGLETON:

```python
# Singleton factory holds configuration
@provider(scope=SINGLETON)
def service_factory(settings: AppSettings) -> ServiceFactory:
    """Singleton factory for creating request-scoped services."""
    return ServiceFactory(settings)

# Request-scoped instances created by factory
@provider(scope=REQUEST)
def my_service(factory: ServiceFactory, session: AsyncSession) -> MyService:
    """Create service instance for this request."""
    return factory.create(session)
```

### HTTP Client

```python
import httpx

@provider(scope=SINGLETON)
def http_client(settings: AppSettings) -> httpx.AsyncClient:
    """
    Shared HTTP client with connection pooling.

    Use SINGLETON to reuse connections across requests.
    """
    return httpx.AsyncClient(
        timeout=settings.http_timeout,
        headers={"User-Agent": settings.app_name},
    )
```

### Cache Service

```python
@provider(scope=SINGLETON)
def cache_service(settings: CacheSettings) -> CacheService:
    """Application-wide cache."""
    if settings.redis_url:
        return RedisCacheService(settings.redis_url)
    return InMemoryCacheService()
```

### Repository Pattern

```python
@provider(scope=REQUEST)
def user_repository(session: AsyncSession) -> UserRepository:
    """User repository for database operations."""
    return UserRepository(session)

@provider(scope=REQUEST)
def order_repository(session: AsyncSession) -> OrderRepository:
    """Order repository for database operations."""
    return OrderRepository(session)
```

### With Qualifiers

```python
from myfy.core import provider, SINGLETON, Qualifier
from typing import Annotated

@provider(scope=SINGLETON, qualifier="primary")
def primary_database(settings: Settings) -> Database:
    """Primary database for writes."""
    return Database(settings.primary_db_url)

@provider(scope=SINGLETON, qualifier="replica")
def replica_database(settings: Settings) -> Database:
    """Replica database for reads."""
    return Database(settings.replica_db_url)

# Usage in routes
@route.get("/users")
async def list_users(
    db: Annotated[Database, Qualifier("replica")]
) -> list[dict]:
    return await db.fetch_all("SELECT * FROM users")
```

## Scope Rules

1. **SINGLETON** can only depend on other **SINGLETON** providers
2. **REQUEST** can depend on **SINGLETON** or **REQUEST** providers
3. **TASK** can depend on **SINGLETON** or **TASK** providers

**Invalid (will fail at startup):**
```python
@provider(scope=SINGLETON)
def bad_service(session: AsyncSession):  # AsyncSession is REQUEST!
    return MyService(session)
```

## Guidelines

- Return type annotation is required
- Use descriptive docstrings
- Keep provider functions pure (no side effects)
- SINGLETON providers should be thread-safe
- REQUEST/TASK providers can hold state
