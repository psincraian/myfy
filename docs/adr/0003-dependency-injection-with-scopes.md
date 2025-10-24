# ADR-0003: Dependency Injection with Scopes

## Status

Accepted

## Context

The myfy framework needs a way to manage dependencies across different lifecycles:
- **Framework-level services** (logger, metrics) that live for the entire application lifetime
- **Request-scoped dependencies** (database connections, user context) that should be created per HTTP request and cleaned up afterward
- **Task-scoped dependencies** (background job context) that exist for a specific async task

Without proper scope management, we risk:
1. **Memory leaks** - request-scoped objects never being cleaned up
2. **Resource exhaustion** - database connections not being pooled/released properly
3. **State leakage** - sharing mutable state across requests unintentionally
4. **Context confusion** - accessing request data from background tasks

Many Python frameworks either:
- Use global state (Flask's `g`, thread-locals) which breaks with async
- Require manual lifecycle management (FastAPI Depends every time)
- Lack clear scope boundaries

The framework is async-native (Principle #9: "Async-native, context-aware"), using contextvars for proper async context propagation.

## Decision

We will implement a **dependency injection container with explicit scopes**: `SINGLETON`, `REQUEST`, and `TASK`.

### Scope Definitions

1. **SINGLETON** - created once at application startup
   - Examples: Logger, Metrics, Configuration, Database Pool
   - Shared across all requests and tasks
   - Thread-safe and immutable
   - Lives until application shutdown

2. **REQUEST** - created per HTTP request
   - Examples: Database Session, Request Context, User Session
   - Isolated per request via contextvars
   - Automatically cleaned up after request completes
   - Cannot be accessed outside request context

3. **TASK** - created per async task/background job
   - Examples: Task Context, Job-specific Logger
   - Isolated per task via contextvars
   - Automatically cleaned up after task completes
   - Cannot be accessed outside task context

### Implementation

```python
from myfy.core import provider, SINGLETON, REQUEST, TASK

# Singleton - shared across app
@provider(scope=SINGLETON)
def database_pool(settings: DatabaseSettings) -> DatabasePool:
    return DatabasePool(settings.database_url)

# Request-scoped - new instance per request
@provider(scope=REQUEST)
def db_session(pool: DatabasePool) -> DatabaseSession:
    session = pool.get_session()
    yield session
    session.close()

# Task-scoped - new instance per background task
@provider(scope=TASK)
def task_context(task_id: str) -> TaskContext:
    ctx = TaskContext(task_id)
    yield ctx
    ctx.cleanup()
```

### Dependency Resolution

- **Singleton** dependencies can depend on other singletons
- **Request** dependencies can depend on singletons and other request-scoped deps
- **Task** dependencies can depend on singletons and other task-scoped deps
- **Singletons cannot depend on request/task scoped dependencies** (enforced at startup)

### Context Propagation

Using Python's `contextvars`:
```python
from contextvars import ContextVar

_request_container: ContextVar[Container] = ContextVar('request_container')

# In middleware
async def request_middleware(request, handler):
    request_container = Container(parent=app_container)
    _request_container.set(request_container)
    try:
        return await handler(request)
    finally:
        await request_container.cleanup()
```

This ensures:
- Each async task has its own dependency container
- No cross-request contamination
- Proper cleanup even with exceptions

## Consequences

### Positive
- **Explicit Lifecycle**: Clear understanding of when dependencies are created/destroyed
- **Async-Safe**: Contextvars ensure proper isolation in async contexts
- **Resource Management**: Automatic cleanup prevents leaks
- **Type-Safe**: Dependency resolution is fully typed
- **Testable**: Easy to override scopes in tests (e.g., use singleton DB for speed)
- **Predictable**: No hidden global state or thread-locals
- **Composable**: Scoped dependencies can depend on parent scope dependencies

### Neutral
- **Learning Curve**: Developers need to understand scope semantics
- **Explicit Declarations**: Must declare scope when registering providers

### Negative
- **Verbosity**: Need to specify scope for each provider
- **Scope Violations**: Attempting to inject request-scoped dep in singleton will fail at startup
- **Container Overhead**: Small performance cost for managing scoped containers

## Alternatives Considered

### 1. Global State (Flask-style `g`)
**Rejected** because:
- Not async-safe (uses thread-locals)
- Hard to test (global state)
- No type safety
- Difficult to reason about lifecycle

### 2. FastAPI's Depends Pattern
**Rejected** because:
- Requires `Depends()` at every injection point (verbose)
- No first-class scope management
- Cleanup relies on generator functions only
- Less discoverable (must know to look for Depends)

### 3. No Scopes (Everything Singleton)
**Rejected** because:
- Memory leaks from request-scoped objects
- Resource exhaustion (unclosed DB connections)
- State leakage between requests
- Not safe for concurrent requests

### 4. Manual Lifecycle Management
**Rejected** because:
- Error-prone (easy to forget cleanup)
- Boilerplate in every handler
- No framework support for patterns
- Hard to test

### 5. Separate Container Per Request (No Parent)
**Rejected** because:
- Wastes memory (duplicates singletons)
- Slower (re-resolves singletons)
- More complex than needed

## References

- [PRINCIPLES.md](/Users/petru/workplace/myfy/PRINCIPLES.md) - Principle #13: Dependency injection with scopes
- [contextvars documentation](https://docs.python.org/3/library/contextvars.html) - Python's context variables
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) - Similar pattern in FastAPI
- [Dependency Injection in .NET](https://learn.microsoft.com/en-us/dotnet/core/extensions/dependency-injection) - Scope inspiration
