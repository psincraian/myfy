# myfy-core

The core kernel of the myfy framework, providing the foundational architecture for building modular Python applications.

## Overview

`myfy-core` is the heart of the myfy framework. It provides the essential building blocks: dependency injection, configuration management, module system, and application lifecycle. All other myfy modules build on top of this foundation.

## Installation

```bash
# Install core only
pip install myfy-core

# Or with uv
uv pip install myfy-core
```

## Key Features

### Dependency Injection

Type-based dependency injection with compile-time resolution and multiple scopes:

- **Zero reflection on hot path** - All analysis happens at startup
- **Type-safe** - Leverages Python's type hints
- **Scope support** - `SINGLETON`, `REQUEST`, and `TASK` scopes
- **Cycle detection** - Catches circular dependencies at startup

```python
from myfy.core import provider, SINGLETON, REQUEST

@provider(scope=SINGLETON)
def database(settings: Settings) -> Database:
    return Database(settings.db_url)

@provider(scope=REQUEST)
def unit_of_work(db: Database) -> UnitOfWork:
    return UnitOfWork(db)
```

### Configuration System

Environment-based configuration with Pydantic validation:

```python
from myfy.core import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    app_name: str = Field(default="My App")
    db_url: str
    debug: bool = False
```

**Profile support:**
```bash
# Set profile via environment variable
export MYFY_PROFILE=dev  # Loads .env.dev
export MYFY_PROFILE=prod # Loads .env.prod
```

### Module System

First-class modules with lifecycle hooks:

```python
from myfy.core import BaseModule

class DataModule(BaseModule):
    async def start(self):
        """Called when application starts."""
        await self.db.connect()
        print("Database connected")

    async def stop(self):
        """Called when application stops."""
        await self.db.disconnect()
        print("Database disconnected")

# Modules start in order, stop in reverse
app.add_module(DataModule())
app.add_module(WebModule())
```

### Application Lifecycle

Predictable, deterministic lifecycle:

1. **Init Phase** - Load configuration, create container
2. **Start Phase** - Start modules in order
3. **Run Phase** - Execute application
4. **Stop Phase** - Stop modules in reverse order

```python
from myfy.core import Application

app = Application(settings_class=Settings)
app.add_module(DataModule())

# Lifecycle managed automatically
await app.run()
```

## Core Concepts

### Dependency Scopes

**SINGLETON** - One instance per application:
```python
@provider(scope=SINGLETON)
def cache() -> Cache:
    return Cache()  # Created once, reused forever
```

**REQUEST** - One instance per HTTP request:
```python
@provider(scope=REQUEST)
def db_session(db: Database) -> Session:
    session = db.create_session()
    yield session
    session.close()  # Cleanup after request
```

**TASK** - One instance per background task:
```python
@provider(scope=TASK)
def task_context() -> TaskContext:
    return TaskContext()  # New instance per task
```

### Provider Functions

Providers are functions that create and configure dependencies:

```python
@provider(scope=SINGLETON)
def logger(settings: Settings) -> Logger:
    """Dependencies can be injected into providers."""
    return Logger(
        level=settings.log_level,
        format=settings.log_format
    )
```

### Auto-Discovery

Automatically discover and register providers and routes:

```python
# Enable auto-discovery (default)
app = Application(auto_discover=True)

# Or manually import modules
app = Application(auto_discover=False)
import my_providers  # Must import to register
import my_routes
```

## Common Patterns

### Service Layer

```python
class UserService:
    def __init__(self, repo: UserRepository, cache: Cache):
        self.repo = repo
        self.cache = cache

    async def get_user(self, user_id: int) -> User:
        # Check cache first
        cached = await self.cache.get(f"user:{user_id}")
        if cached:
            return cached

        # Fetch from database
        user = await self.repo.get(user_id)
        await self.cache.set(f"user:{user_id}", user)
        return user

@provider(scope=SINGLETON)
def user_service(repo: UserRepository, cache: Cache) -> UserService:
    return UserService(repo, cache)
```

### Repository Pattern

```python
class UserRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get(self, user_id: int) -> User | None:
        result = await self.db.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        )
        return User(**result) if result else None

@provider(scope=SINGLETON)
def user_repository(db: Database) -> UserRepository:
    return UserRepository(db)
```

### Database Connection

```python
class Database:
    def __init__(self, url: str):
        self.url = url
        self.pool = None

    async def connect(self):
        self.pool = await create_pool(self.url)

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

class DatabaseModule(BaseModule):
    def __init__(self, db: Database):
        self.db = db

    async def start(self):
        await self.db.connect()

    async def stop(self):
        await self.db.disconnect()

@provider(scope=SINGLETON)
def database(settings: Settings) -> Database:
    return Database(settings.db_url)

@provider(scope=SINGLETON)
def database_module(db: Database) -> DatabaseModule:
    return DatabaseModule(db)
```

## Best Practices

### Use Type Hints

Type hints are required for dependency injection:

```python
# ✓ Good
@provider(scope=SINGLETON)
def service(config: Config) -> MyService:
    return MyService(config)

# ✗ Bad - No type hints
@provider(scope=SINGLETON)
def service(config):  # Won't work!
    return MyService(config)
```

### Prefer Constructor Injection

```python
# ✓ Good - Dependencies are explicit
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

# ✗ Avoid - Hidden dependencies
class UserService:
    def process(self, repo: UserRepository):  # Injected per method
        pass
```

### Use Appropriate Scopes

```python
# ✓ Good - Expensive resources are singletons
@provider(scope=SINGLETON)
def database_pool(settings: Settings) -> Pool:
    return create_pool(settings.db_url)

# ✗ Bad - Creates new pool per request!
@provider(scope=REQUEST)
def database_pool(settings: Settings) -> Pool:
    return create_pool(settings.db_url)
```

### Keep Modules Focused

```python
# ✓ Good - Single responsibility
class DatabaseModule(BaseModule):
    async def start(self):
        await self.db.connect()

# ✗ Bad - Too many responsibilities
class EverythingModule(BaseModule):
    async def start(self):
        await self.db.connect()
        await self.cache.connect()
        await self.queue.connect()
        # Too much!
```

## Examples

### Minimal Application

```python
from myfy.core import Application

app = Application(auto_discover=False)

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run())
```

### Application with Settings

```python
from myfy.core import Application, BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    app_name: str = Field(default="My App")
    debug: bool = False

app = Application(settings_class=Settings, auto_discover=False)
```

### Application with Module

```python
from myfy.core import Application, BaseModule

class MyModule(BaseModule):
    async def start(self):
        print("Module started!")

app = Application(auto_discover=False)
app.add_module(MyModule())
```

## Next Steps

- **Add Web Support**: Install [`myfy-web`](web.md) for HTTP routing
- **Add CLI Tools**: Install [`myfy-cli`](cli.md) for development commands
- **Add Frontend**: Install [`myfy-frontend`](frontend.md) for UI templates
- **Learn DI**: Read [Dependency Injection](../core-concepts/dependency-injection.md) guide
- **Learn Modules**: Read [Modules](../core-concepts/modules.md) guide
