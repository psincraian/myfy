---
name: dependency-injection
description: myfy dependency injection with scopes (SINGLETON, REQUEST, TASK). Use when working with @provider decorator, DI container, scopes, injection patterns, or understanding how WebModule, DataModule, FrontendModule, TasksModule, UserModule, CliModule, AuthModule, and RateLimitModule use dependency injection.
---

# Dependency Injection in myfy

myfy uses constructor-based dependency injection with three scopes.

## Scopes

| Scope | Lifetime | Use Case |
|-------|----------|----------|
| SINGLETON | Application lifetime | Config, pools, services, caches |
| REQUEST | Per HTTP request | Sessions, user context, request logger |
| TASK | Per background task | Task context, job-specific state |

## Provider Declaration

```python
from myfy.core import provider, SINGLETON, REQUEST, TASK

# SINGLETON: Created once, shared across all requests
@provider(scope=SINGLETON)
def database_pool(settings: DatabaseSettings) -> DatabasePool:
    return DatabasePool(settings.database_url)

# REQUEST: Created per HTTP request, auto-cleaned up
@provider(scope=REQUEST)
def db_session(pool: DatabasePool) -> AsyncSession:
    return pool.get_session()

# TASK: Created per background task execution
@provider(scope=TASK)
def task_logger(ctx: TaskContext) -> Logger:
    return Logger(task_id=ctx.task_id)
```

## Provider Options

```python
@provider(
    scope=SINGLETON,              # Lifecycle scope
    qualifier="primary",          # Optional qualifier for multiple providers
    name="my_database",           # Optional name for resolution
    reloadable=("log_level",),    # Settings that can hot-reload
)
def database(settings: Settings) -> Database:
    return Database(settings.db_url)
```

## Scope Dependency Rules

1. **SINGLETON** can depend on: other singletons only
2. **REQUEST** can depend on: singletons and other request-scoped
3. **TASK** can depend on: singletons and other task-scoped

**SINGLETON cannot depend on REQUEST/TASK** - this fails at compile time!

```python
# WRONG - will fail at startup
@provider(scope=SINGLETON)
def bad_service(session: AsyncSession):  # AsyncSession is REQUEST scope
    return MyService(session)

# CORRECT - use factory pattern
@provider(scope=SINGLETON)
def service_factory(pool: DatabasePool) -> ServiceFactory:
    return ServiceFactory(pool)

@provider(scope=REQUEST)
def service(factory: ServiceFactory, session: AsyncSession) -> MyService:
    return factory.create(session)
```

## Injection in Routes

Parameters are auto-classified in order:
1. **Path parameters** - from URL template like `{user_id}`
2. **Query parameters** - annotated with `Query(...)` or primitives with defaults
3. **Body parameter** - Pydantic model or dataclass
4. **DI dependencies** - everything else (resolved from container)

```python
from myfy.web import route, Query
from myfy.data import AsyncSession

@route.post("/users/{user_id}/orders")
async def create_order(
    user_id: int,                    # Path param
    limit: int = Query(default=10),  # Query param
    body: OrderCreate,               # Request body (Pydantic model)
    session: AsyncSession,           # DI (REQUEST scope)
    settings: AppSettings,           # DI (SINGLETON)
) -> dict:
    ...
```

## Qualifiers for Multiple Providers

When you have multiple providers of the same type:

```python
from myfy.core import provider, SINGLETON, Qualifier
from typing import Annotated

@provider(scope=SINGLETON, qualifier="primary")
def primary_db(settings: Settings) -> Database:
    return Database(settings.primary_url)

@provider(scope=SINGLETON, qualifier="replica")
def replica_db(settings: Settings) -> Database:
    return Database(settings.replica_url)

# Inject by qualifier
@route.get("/users")
async def list_users(
    db: Annotated[Database, Qualifier("replica")]
) -> list[dict]:
    return await db.fetch_all()
```

## Common Patterns

### Factory Pattern (REQUEST from SINGLETON)

```python
@provider(scope=SINGLETON)
def email_client(settings: EmailSettings) -> EmailClient:
    return EmailClient(settings.api_key)

@provider(scope=REQUEST)
def email_sender(client: EmailClient, user: User) -> EmailSender:
    return EmailSender(client, from_user=user)
```

### Optional Dependencies

```python
from typing import Optional

@provider(scope=SINGLETON)
def cache_service(redis: Optional[RedisClient] = None) -> CacheService:
    if redis:
        return RedisCacheService(redis)
    return InMemoryCacheService()
```

## Testing

Override providers in tests using the container's override context:

```python
from myfy.core import override

async def test_with_mock_db():
    mock_db = MockDatabase()

    with override(Database, mock_db):
        # Inside this block, Database resolves to mock_db
        result = await my_service.do_something()

    assert result == expected
```

## Best Practices

1. **Keep providers pure** - No side effects in factory functions
2. **Use SINGLETON for shared resources** - Database pools, HTTP clients, caches
3. **Use REQUEST for request-specific state** - DB sessions, user context
4. **Use TASK for background job state** - Task logger, job-specific clients
5. **Validate at compile time** - All scope violations caught at startup
6. **Return type required** - Provider functions must have return type annotation
