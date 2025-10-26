# Application Lifecycle

Understanding myfy's application lifecycle helps you manage resources, handle errors, and build reliable applications.

---

## Lifecycle Phases

1. App Creation
2. Initialization
3. Starting Modules
4. Running
5. Shutdown Signal
6. Stopping Modules
7. Exiting

---

## Phase 1: Creation

```python
from myfy.core import Application

# Create application instance
app = Application(settings_class=Settings, auto_discover=False)
app.add_module(WebModule())
app.add_module(DataModule())
```

**What happens:**
- Settings class is stored
- Modules are collected
- No providers registered yet
- No connections made yet

---

## Phase 2: Initialize

```python
app.initialize()
```

**What happens:**
1. Load settings from environment
2. Validate settings with Pydantic
3. Create DI container
4. Call `module.configure(container)` on each module
5. Register all providers
6. Build dependency graph
7. Detect cycles
8. Validate scopes
9. Cache injection plans

**When it runs:**
- Explicitly via `app.initialize()`
- Automatically on first `app.run()`
- Automatically by CLI commands

---

## Phase 3: Start Modules

```python
await app.start_modules()
```

**What happens:**
1. Call `await module.start()` on each module (in order)
2. Connect to databases
3. Open network connections
4. Start background tasks
5. Warm up caches

**Order:** Modules start in the order they were added.

---

## Phase 4: Run

```python
await app.run()
```

**What happens:**
- Start all modules (if not already started)
- Run the main application loop
- For WebModule: Start ASGI server
- Handle SIGTERM and SIGINT gracefully

**Blocking:** This method blocks until shutdown signal received.

---

## Phase 5: Stop Modules

```python
await app.stop_modules()
```

**What happens:**
1. Call `await module.stop()` on each module (reverse order)
2. Close database connections
3. Stop background tasks
4. Flush buffers
5. Release resources

**Order:** Modules stop in reverse order (last added stops first).

---

## Complete Example

```python
from myfy.core import Application, BaseModule
from myfy.web import WebModule

class DataModule(BaseModule):
    def __init__(self):
        super().__init__("data")
        self.db = None

    def configure(self, container: Container) -> None:
        print("1. DataModule.configure()")
        # Register providers

    async def start(self) -> None:
        print("3. DataModule.start()")
        self.db = Database(settings.database_url)
        await self.db.connect()

    async def stop(self) -> None:
        print("5. DataModule.stop()")
        if self.db:
            await self.db.disconnect()

# Create app
app = Application(settings_class=Settings, auto_discover=False)
app.add_module(DataModule())  # Added first
app.add_module(WebModule())   # Added second

# Initialize
print("Phase: Initialize")
app.initialize()
# Output:
# 1. DataModule.configure()
# 2. WebModule.configure()

# Run
print("Phase: Start & Run")
await app.run()
# Output:
# 3. DataModule.start()
# 4. WebModule.start()
# ... application runs ...
# (user presses Ctrl+C)
# 6. WebModule.stop()
# 5. DataModule.stop()
```

---

## Graceful Shutdown

myfy handles shutdown signals automatically:

### Signals Handled

- **SIGTERM** - From `kill` command or container orchestrator
- **SIGINT** - From Ctrl+C in terminal

### Shutdown Process

```python
# Application receives signal
→ Log: "Received shutdown signal"
→ Stop accepting new requests
→ Wait for in-flight requests (max 30s)
→ Call module.stop() in reverse order
→ Exit with code 0
```

### Custom Shutdown Logic

```python
class MyModule(BaseModule):
    async def stop(self) -> None:
        print("Shutting down gracefully...")

        # Finish in-flight work
        await self.task_queue.wait_empty(timeout=30)

        # Flush buffers
        await self.metrics.flush()

        # Close connections
        await self.db.disconnect()

        print("Shutdown complete")
```

---

## Error Handling

### Startup Errors

```python
class DataModule(BaseModule):
    async def start(self) -> None:
        try:
            await self.db.connect()
        except ConnectionError as e:
            print(f"Failed to connect to database: {e}")
            raise  # Application will exit

# If module.start() raises, app exits with error code 1
```

### Runtime Errors

```python
@route.get("/users")
async def list_users(db: Database) -> list[User]:
    try:
        return await db.get_all_users()
    except DatabaseError as e:
        # Handle error
        raise HTTPException(status_code=500, detail="Database error")
```

### Shutdown Errors

```python
class MyModule(BaseModule):
    async def stop(self) -> None:
        try:
            await self.cleanup()
        except Exception as e:
            # Log but don't prevent other modules from stopping
            print(f"Error during cleanup: {e}")
```

---

## Testing Lifecycle

### Manual Control

```python
import pytest

@pytest.fixture
async def app():
    app = Application(settings_class=TestSettings, auto_discover=False)
    app.add_module(DataModule())

    # Initialize
    app.initialize()

    # Start
    await app.start_modules()

    yield app

    # Stop
    await app.stop_modules()

@pytest.mark.asyncio
async def test_user_creation(app):
    service = app.container.get(UserService)
    user = await service.create_user("test@example.com")
    assert user.email == "test@example.com"
```

---

## Best Practices

### ✅ DO

- Initialize connections in `module.start()`
- Close connections in `module.stop()`
- Handle errors in `start()` and fail fast
- Log lifecycle events
- Wait for in-flight work before stopping
- Test lifecycle hooks

### ❌ DON'T

- Don't open connections in `configure()`
- Don't skip cleanup in `stop()`
- Don't ignore errors in `start()`
- Don't block indefinitely in `stop()`
- Don't access container outside `configure()`

---

## Advanced Patterns

### Dependent Module Startup

```python
class CacheModule(BaseModule):
    async def start(self) -> None:
        # Wait for database to be ready
        db = self.container.get(Database)
        await db.wait_ready(timeout=30)

        # Now start cache
        self.cache = Cache(db)
        await self.cache.warm_up()
```

### Healthchecks

```python
class DataModule(BaseModule):
    async def is_healthy(self) -> bool:
        """Check if module is healthy."""
        try:
            await self.db.ping()
            return True
        except Exception:
            return False

# In route
@route.get("/health")
async def health_check(app: Application) -> dict:
    checks = {}
    for module in app.modules:
        if hasattr(module, 'is_healthy'):
            checks[module.name] = await module.is_healthy()
    return {"healthy": all(checks.values()), "checks": checks}
```

### Periodic Tasks

```python
class MetricsModule(BaseModule):
    async def start(self) -> None:
        # Start background task
        self.task = asyncio.create_task(self._collect_metrics())

    async def stop(self) -> None:
        # Cancel background task
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass

    async def _collect_metrics(self) -> None:
        while True:
            await self.collect()
            await asyncio.sleep(60)  # Every minute
```

---

## Troubleshooting

### Module Won't Start

```
Error: DataModule failed to start: Connection refused
```

**Solution:** Check that dependencies (database, redis, etc.) are running:
```bash
# Check if PostgreSQL is running
pg_isready

# Check if Redis is running
redis-cli ping
```

### Slow Shutdown

```
Warning: Shutdown taking longer than expected
```

**Solution:** Reduce timeout or fix blocking code:
```python
async def stop(self) -> None:
    # Add timeout
    try:
        await asyncio.wait_for(self.cleanup(), timeout=10)
    except asyncio.TimeoutError:
        print("Cleanup timed out, forcing shutdown")
```

### Module Stops in Wrong Order

```
Error: Cache stopped before Database
```

**Solution:** Add modules in correct order:
```python
# Database should be added before Cache
app.add_module(DataModule())  # First
app.add_module(CacheModule())  # Second (depends on DataModule)
```

---

## CLI Lifecycle

When using `myfy run`:

```bash
uv run myfy run
```

**Lifecycle:**
```
1. CLI discovers app.py
2. Loads Application instance
3. Calls app.initialize()
4. Calls app.start_modules()
5. Starts uvicorn with ASGI app
6. (Ctrl+C pressed)
7. Uvicorn stops accepting requests
8. Calls app.stop_modules()
9. Exits
```

---

## Next Steps

- [Modules](modules.md) - Create custom modules
- [Dependency Injection](dependency-injection.md) - Use DI in lifecycle
- [Testing Guide](../guides/testing.md) - Test lifecycle
- [Deployment](../guides/deployment.md) - Production lifecycle
