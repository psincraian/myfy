# Dependency Injection

myfy's DI system provides compile-time resolution, scoped lifetimes, and zero reflection on hot paths.

---

## Why DI?

Dependency Injection solves three core problems:

1. **Testability** - Easy to mock dependencies
2. **Flexibility** - Swap implementations without changing code
3. **Decoupling** - Components don't create their dependencies

---

## Basic Usage

### Register a Provider

```python
from myfy.core import provider, SINGLETON

@provider(scope=SINGLETON)
def database(settings: Settings) -> Database:
    return Database(settings.db_url)
```

### Inject Dependencies

```python
@route.get("/users")
async def list_users(db: Database) -> list[User]:
    return await db.get_all_users()
```

That's it! myfy automatically:
1. Detects the `db: Database` dependency
2. Looks up the provider for `Database`
3. Calls the provider with its dependencies
4. Injects the result into your handler

---

## Scopes

myfy provides three scopes for different lifetimes:

### `SINGLETON` Scope

One instance per application. Perfect for:
- Database connection pools
- Configuration objects
- Caches
- HTTP clients

```python
@provider(scope=SINGLETON)
def cache(settings: Settings) -> Cache:
    return Redis(settings.redis_url)
```

### `REQUEST` Scope

One instance per HTTP request. Perfect for:
- Database sessions/transactions
- Request-specific context
- Per-request caches

```python
@provider(scope=REQUEST)
def session(db: Database) -> Session:
    return db.create_session()
```

### `TASK` Scope

One instance per background task. Perfect for:
- Task-specific resources
- Isolated task context

```python
@provider(scope=TASK)
def task_context() -> TaskContext:
    return TaskContext()
```

---

## How It Works

### Compile-Time Resolution

myfy analyzes dependencies at startup, not at request time:

```python
# Startup (once):
# 1. Parse type hints from handlers
# 2. Build dependency graph
# 3. Detect cycles
# 4. Create injection plans
# 5. Cache plans in O(1) lookup table

# Request time (fast):
# 1. Lookup injection plan (O(1))
# 2. Execute plan (simple function calls)
# 3. Call handler
```

**Result:** Zero reflection overhead on hot path.

### Dependency Graph

```python
@provider(scope=SINGLETON)
def database(settings: Settings) -> Database:
    return Database(settings.db_url)

@provider(scope=REQUEST)
def session(db: Database) -> Session:
    return db.create_session()

@provider(scope=REQUEST)
def user_repository(session: Session) -> UserRepository:
    return UserRepository(session)

@route.get("/users")
async def list_users(repo: UserRepository) -> list[User]:
    return await repo.list_all()
```

Dependency graph:
```
Settings (built-in)
   ↓
Database (SINGLETON)
   ↓
Session (REQUEST)
   ↓
UserRepository (REQUEST)
   ↓
list_users (handler)
```

---

## Advanced Patterns

### Factory Functions

```python
@provider(scope=SINGLETON)
def create_database(settings: Settings) -> Database:
    if settings.db_type == "postgres":
        return PostgresDatabase(settings.postgres_url)
    elif settings.db_type == "mysql":
        return MySQLDatabase(settings.mysql_url)
    else:
        raise ValueError(f"Unknown db_type: {settings.db_type}")
```

### Constructor Injection

```python
class UserService:
    def __init__(self, repo: UserRepository, cache: Cache):
        self.repo = repo
        self.cache = cache

    async def get_user(self, user_id: int) -> User:
        # Check cache
        cached = await self.cache.get(f"user:{user_id}")
        if cached:
            return User.model_validate(cached)

        # Get from database
        user = await self.repo.get(user_id)
        if user:
            await self.cache.set(f"user:{user_id}", user.model_dump())
        return user

@provider(scope=SINGLETON)
def user_service(repo: UserRepository, cache: Cache) -> UserService:
    return UserService(repo, cache)
```

### Multiple Implementations

```python
# Abstract interface
class Storage(Protocol):
    async def save(self, key: str, value: Any) -> None: ...
    async def load(self, key: str) -> Any: ...

# Implementations
class RedisStorage:
    async def save(self, key: str, value: Any) -> None:
        await redis.set(key, value)

class S3Storage:
    async def save(self, key: str, value: Any) -> None:
        await s3.put_object(key, value)

# Register based on config
@provider(scope=SINGLETON)
def storage(settings: Settings) -> Storage:
    if settings.storage_type == "redis":
        return RedisStorage(settings.redis_url)
    elif settings.storage_type == "s3":
        return S3Storage(settings.s3_bucket)
    else:
        raise ValueError(f"Unknown storage_type: {settings.storage_type}")
```

---

## Request Scope Deep Dive

### How Request Scope Works

Request-scoped dependencies use Python's `contextvars`:

```python
from contextvars import ContextVar

_request_bag: ContextVar[dict[str, Any]] = ContextVar("request_bag")

# At request start:
_request_bag.set({})

# When resolving REQUEST-scoped dependency:
bag = _request_bag.get()
if "session" not in bag:
    bag["session"] = create_session()
return bag["session"]

# At request end:
_request_bag.set({})  # Clear the bag
```

### Lifecycle

```
HTTP Request arrives
    ↓
Create request context (contextvar)
    ↓
Resolve REQUEST-scoped dependencies
    ↓
Execute handler
    ↓
Clear request context
    ↓
Response sent
```

### Example: Database Session

```python
@provider(scope=REQUEST)
def session(engine: Engine) -> AsyncSession:
    """Create a new database session for each request."""
    return AsyncSession(engine)

@route.post("/users")
async def create_user(
    body: CreateUserDTO,
    session: AsyncSession
) -> User:
    # Same session instance throughout the request
    user = User(**body.model_dump())
    session.add(user)
    await session.commit()
    return user
```

---

## Scope Validation

myfy validates scopes at compile-time:

### Valid: Singleton → Singleton

```python
@provider(scope=SINGLETON)
def cache() -> Cache:
    return Cache()

@provider(scope=SINGLETON)
def service(cache: Cache) -> Service:  # ✅ OK
    return Service(cache)
```

### Invalid: Singleton → Request

```python
@provider(scope=REQUEST)
def session() -> Session:
    return Session()

@provider(scope=SINGLETON)
def service(session: Session) -> Service:  # ❌ ERROR
    # Singleton can't depend on REQUEST scope!
    return Service(session)
```

**Why?** A singleton lives for the entire application, but a request-scoped dependency is recreated per request. This would be a lifetime mismatch.

### Scope Hierarchy

```
SINGLETON (longest lifetime)
    ↓
REQUEST
    ↓
TASK (shortest lifetime)
```

**Rule:** Dependencies can only inject from equal or longer lifetimes.

---

## Cycle Detection

myfy detects circular dependencies at startup:

```python
@provider(scope=SINGLETON)
def service_a(b: ServiceB) -> ServiceA:
    return ServiceA(b)

@provider(scope=SINGLETON)
def service_b(a: ServiceA) -> ServiceB:
    return ServiceB(a)

# At startup:
# Error: Circular dependency detected:
#   ServiceA → ServiceB → ServiceA
```

---

## Testing with DI

### Override Dependencies

```python
import pytest
from myfy.core import Application, provider, SINGLETON

@pytest.fixture
def app():
    app = Application(settings_class=TestSettings, auto_discover=False)

    # Override database with mock
    @provider(scope=SINGLETON)
    def mock_database() -> Database:
        return MockDatabase()

    app.initialize()
    return app

def test_user_creation(app):
    service = app.container.get(UserService)
    user = await service.create_user("test@example.com")
    assert user.email == "test@example.com"
```

### Mock Dependencies

```python
from unittest.mock import Mock

@pytest.fixture
def mock_cache():
    cache = Mock(spec=Cache)
    cache.get.return_value = None
    cache.set.return_value = None
    return cache

@pytest.fixture
def user_service(mock_cache):
    repo = InMemoryUserRepository()
    return UserService(repo, mock_cache)

def test_user_service(user_service, mock_cache):
    user = await user_service.get_user(1)
    mock_cache.get.assert_called_once_with("user:1")
```

---

## Performance

### Benchmark: DI Resolution

```
Plain function call:     100ns
myfy DI injection:       150ns
Overhead:                 50ns (0.05 microseconds)
```

myfy's DI adds minimal overhead because:
1. Type hints parsed once at startup
2. Injection plans cached in dict (O(1))
3. No reflection during requests
4. Simple function calls only

---

## Common Patterns

### Service Layer

```python
@provider(scope=SINGLETON)
def user_service(
    repo: UserRepository,
    cache: Cache,
    email: EmailService
) -> UserService:
    return UserService(repo, cache, email)

@route.post("/users")
async def create_user(
    body: CreateUserDTO,
    service: UserService
) -> User:
    return await service.create_user(body)
```

### Unit of Work

```python
@provider(scope=REQUEST)
def unit_of_work(session: AsyncSession) -> UnitOfWork:
    return UnitOfWork(session)

@route.post("/orders")
async def create_order(
    body: CreateOrderDTO,
    uow: UnitOfWork
) -> Order:
    order = await uow.orders.create(body)
    await uow.commit()
    return order
```

### Repository Pattern

```python
@provider(scope=SINGLETON)
def user_repository(session_factory: SessionFactory) -> UserRepository:
    return SQLAlchemyUserRepository(session_factory)

@route.get("/users/{user_id}")
async def get_user(
    user_id: int,
    repo: UserRepository
) -> User:
    return await repo.get(user_id)
```

---

## Best Practices

### ✅ DO

- Use `SINGLETON` for stateless services
- Use `REQUEST` for database sessions
- Keep providers simple and focused
- Inject interfaces, not implementations
- Test by mocking dependencies

### ❌ DON'T

- Don't inject REQUEST scope into SINGLETON
- Don't store mutable state in SINGLETON
- Don't create dependencies manually
- Don't use global variables
- Don't bypass the container

---

## Troubleshooting

### Missing Provider

```
Error: No provider found for type 'Database'
```

**Solution:** Register a provider:
```python
@provider(scope=SINGLETON)
def database(settings: Settings) -> Database:
    return Database(settings.db_url)
```

### Circular Dependency

```
Error: Circular dependency detected: ServiceA → ServiceB → ServiceA
```

**Solution:** Refactor to remove the cycle:
- Extract shared logic into a third service
- Use callbacks or events instead of direct injection

### Scope Mismatch

```
Error: Cannot inject REQUEST-scoped dependency into SINGLETON
```

**Solution:** Change the dependent scope or use a factory:
```python
# Instead of:
@provider(scope=SINGLETON)
def service(session: Session) -> Service:  # ❌
    return Service(session)

# Use:
@provider(scope=REQUEST)
def service(session: Session) -> Service:  # ✅
    return Service(session)
```

---

## Next Steps

- [Modules](modules.md) - Organize your application
- [Configuration](configuration.md) - Type-safe settings
