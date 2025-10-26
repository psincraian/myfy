# Modules

Modules are myfy's way of organizing and composing applications. Think of them as self-contained feature packages with their own dependencies, configuration, and lifecycle.

---

## What is a Module?

A module is a component that:
- Registers services in the DI container
- Has its own lifecycle (start/stop hooks)
- Can depend on other modules
- Is independently testable
- Can be distributed as a package

---

## Built-in Modules

myfy ships with these modules:

| Module | Package | Purpose |
|--------|---------|---------|
| **Core** | `myfy-core` | DI, config, lifecycle management |
| **Web** | `myfy-web` | HTTP/ASGI, routing, handlers |
| **CLI** | `myfy-cli` | Development tools |

---

## Using Modules

### Add a Module

```python
from myfy.core import Application
from myfy.web import WebModule

app = Application(settings_class=Settings, auto_discover=False)
app.add_module(WebModule())
```

### Auto-Discovery

Modules can register themselves via entry points:

```toml
# pyproject.toml
[project.entry-points."myfy.modules"]
data = "myfy_data:data_module"
cache = "myfy_cache:cache_module"
```

```python
# Enable auto-discovery
app = Application(settings_class=Settings, auto_discover=True)
# Automatically loads all registered modules
```

---

## Creating a Module

### Basic Module

```python
from myfy.core import BaseModule, Container, SINGLETON

class DataModule(BaseModule):
    def __init__(self):
        super().__init__("data")

    def configure(self, container: Container) -> None:
        """Register services in the DI container."""
        # Register providers
        container.register(Database, factory=self._create_database, scope=SINGLETON)

    def _create_database(self, settings: Settings) -> Database:
        return Database(settings.database_url)
```

### With Lifecycle Hooks

```python
class DataModule(BaseModule):
    def __init__(self):
        super().__init__("data")
        self.db: Database | None = None

    def configure(self, container: Container) -> None:
        container.register(Database, factory=self._create_database, scope=SINGLETON)

    def _create_database(self, settings: Settings) -> Database:
        return Database(settings.database_url)

    async def start(self) -> None:
        """Called when application starts."""
        print("🔌 Connecting to database...")
        self.db = Database(settings.database_url)
        await self.db.connect()
        print("✅ Database connected")

    async def stop(self) -> None:
        """Called when application stops."""
        if self.db:
            print("🔌 Closing database connection...")
            await self.db.disconnect()
            print("✅ Database closed")
```

---

## Module Lifecycle

Modules follow a predictable lifecycle:

```
Application.initialize()
    ↓
1. CONFIGURE: container.configure() on each module
    ↓
2. VALIDATE: Check for missing providers, cycles
    ↓
Application.run()
    ↓
3. START: module.start() on each module (in order)
    ↓
4. RUN: Application runs (handles requests, etc.)
    ↓
5. STOP: module.stop() on each module (reverse order)
```

---

## Complete Example: Cache Module

```python
from myfy.core import BaseModule, Container, provider, SINGLETON
from redis.asyncio import Redis
from typing import Any


class CacheModule(BaseModule):
    """Redis cache module."""

    def __init__(self, redis_url: str | None = None):
        super().__init__("cache")
        self.redis_url = redis_url
        self.redis: Redis | None = None

    def configure(self, container: Container) -> None:
        """Register cache service."""

        @provider(scope=SINGLETON)
        def cache_service(settings: Settings) -> CacheService:
            url = self.redis_url or settings.redis_url
            return CacheService(url)

        # Provider is automatically registered

    async def start(self) -> None:
        """Connect to Redis."""
        print("🔌 Connecting to Redis...")
        self.redis = Redis.from_url(self.redis_url)
        await self.redis.ping()
        print("✅ Redis connected")

    async def stop(self) -> None:
        """Disconnect from Redis."""
        if self.redis:
            print("🔌 Closing Redis connection...")
            await self.redis.close()
            print("✅ Redis closed")


class CacheService:
    """Cache operations."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis = Redis.from_url(redis_url)

    async def get(self, key: str) -> Any:
        value = await self.redis.get(key)
        return value.decode() if value else None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        await self.redis.set(key, str(value), ex=ttl)

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)
```

### Using the Cache Module

```python
# app.py
from myfy.core import Application
from myfy.web import WebModule
from cache_module import CacheModule

app = Application(settings_class=Settings, auto_discover=False)
app.add_module(WebModule())
app.add_module(CacheModule(redis_url="redis://localhost:6379"))

# In routes
@route.get("/cached/{key}")
async def get_cached(key: str, cache: CacheService) -> dict:
    value = await cache.get(key)
    return {"key": key, "value": value}
```

---

## Module Dependencies

Modules can depend on other modules:

```python
class AuthModule(BaseModule):
    def __init__(self):
        super().__init__("auth")
        # Declare that we need the cache module
        self.required_modules = ["cache", "database"]

    def configure(self, container: Container) -> None:
        # Cache and Database are already registered

        @provider(scope=SINGLETON)
        def auth_service(cache: CacheService, db: Database) -> AuthService:
            return AuthService(cache, db)
```

---

## Distributing Modules

### 1. Create Package Structure

```
myfy-cache/
├── pyproject.toml
├── README.md
└── myfy_cache/
    ├── __init__.py
    └── module.py
```

### 2. Define Entry Point

```toml
# pyproject.toml
[project]
name = "myfy-cache"
version = "0.1.0"
dependencies = ["myfy-core>=0.1.0", "redis>=5.0"]

[project.entry-points."myfy.modules"]
cache = "myfy_cache:cache_module"
```

### 3. Export Module

```python
# myfy_cache/__init__.py
from .module import CacheModule

cache_module = CacheModule()

__all__ = ["CacheModule", "cache_module"]
```

### 4. Users Install and Use

```bash
pip install myfy-cache
```

```python
# Auto-discovered!
app = Application(settings_class=Settings, auto_discover=True)
# CacheModule automatically loaded
```

---

## Advanced Patterns

### Conditional Registration

```python
class DataModule(BaseModule):
    def configure(self, container: Container) -> None:
        settings = container.get(Settings)

        if settings.enable_cache:
            @provider(scope=SINGLETON)
            def cached_repository(db: Database, cache: Cache) -> UserRepository:
                return CachedUserRepository(db, cache)
        else:
            @provider(scope=SINGLETON)
            def basic_repository(db: Database) -> UserRepository:
                return UserRepository(db)
```

### Dynamic Configuration

```python
class DatabaseModule(BaseModule):
    def __init__(self, pool_size: int = 10):
        super().__init__("database")
        self.pool_size = pool_size

    def configure(self, container: Container) -> None:
        @provider(scope=SINGLETON)
        def database(settings: Settings) -> Database:
            return Database(
                settings.database_url,
                pool_size=self.pool_size  # Use module config
            )
```

### Module Events

```python
class MetricsModule(BaseModule):
    async def start(self) -> None:
        # Start collecting metrics
        self.collector = MetricsCollector()
        await self.collector.start()

    async def stop(self) -> None:
        # Flush metrics before shutdown
        await self.collector.flush()
        await self.collector.stop()
```

---

## Testing Modules

### Test Module in Isolation

```python
import pytest
from myfy.core import Application

@pytest.fixture
def app():
    app = Application(settings_class=TestSettings, auto_discover=False)
    app.add_module(CacheModule(redis_url="redis://localhost:6379"))
    app.initialize()
    return app

@pytest.mark.asyncio
async def test_cache_module(app):
    await app.start_modules()

    cache = app.container.get(CacheService)
    await cache.set("test_key", "test_value")
    value = await cache.get("test_key")

    assert value == "test_value"

    await app.stop_modules()
```

### Mock Module Dependencies

```python
@pytest.fixture
def app_with_mocks():
    app = Application(settings_class=TestSettings, auto_discover=False)

    # Override database with mock
    @provider(scope=SINGLETON)
    def mock_database() -> Database:
        return MockDatabase()

    app.add_module(DataModule())
    app.initialize()
    return app
```

---

## Best Practices

### ✅ DO

- Keep modules focused on one feature
- Use lifecycle hooks for resource management
- Register all providers in `configure()`
- Clean up resources in `stop()`
- Make modules independently testable
- Document module dependencies

### ❌ DON'T

- Don't mix concerns in one module
- Don't access container outside `configure()`
- Don't skip cleanup in `stop()`
- Don't create circular module dependencies
- Don't use global state

---

## Module Examples

### Database Module

```python
class DatabaseModule(BaseModule):
    async def start(self) -> None:
        self.engine = create_async_engine(settings.database_url)
        await self.engine.connect()

    async def stop(self) -> None:
        await self.engine.dispose()

    def configure(self, container: Container) -> None:
        @provider(scope=SINGLETON)
        def database() -> Engine:
            return self.engine

        @provider(scope=REQUEST)
        def session(db: Engine) -> AsyncSession:
            return AsyncSession(db)
```

### Background Tasks Module

```python
class TasksModule(BaseModule):
    async def start(self) -> None:
        self.scheduler = Scheduler()
        await self.scheduler.start()

    async def stop(self) -> None:
        await self.scheduler.stop()

    def configure(self, container: Container) -> None:
        @provider(scope=SINGLETON)
        def scheduler() -> Scheduler:
            return self.scheduler
```

### Email Module

```python
class EmailModule(BaseModule):
    def configure(self, container: Container) -> None:
        @provider(scope=SINGLETON)
        def email_service(settings: Settings) -> EmailService:
            return SMTPEmailService(
                host=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
            )
```

---

## Troubleshooting

### Module Not Found

```
Error: Module 'cache' not found
```

**Solution:** Make sure the module is registered:
```python
app.add_module(CacheModule())
```

### Startup Failure

```
Error: Module 'data' failed to start
```

**Solution:** Check the `start()` method:
```python
async def start(self) -> None:
    try:
        await self.connect()
    except Exception as e:
        print(f"Failed to start: {e}")
        raise
```

### Circular Module Dependencies

```
Error: Circular module dependency: auth → cache → auth
```

**Solution:** Refactor to remove the cycle or merge modules.

---

## Next Steps

- [Configuration](configuration.md) - Module configuration
- [Lifecycle](lifecycle.md) - Application lifecycle
- [Building Modules Guide](../guides/building-modules.md) - Detailed tutorial
- [Testing Guide](../guides/testing.md) - Test your modules
